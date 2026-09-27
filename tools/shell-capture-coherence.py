#!/usr/bin/env python3
"""Bounded repeated-observation agreement, never an atomic snapshot guarantee."""
import json

FIELDS = ('report', 'fragment', 'effective', 'mount_context')
LIMITATIONS = ['not an atomic snapshot', 'changes reverted between reads may be missed',
               'manager identity, loaded bytes and unqueried state are not proven']


def observations(evidence):
    return {key: evidence[key] for key in FIELDS if key in evidence}


def complete(value):
    if not isinstance(value, dict) or set(value) != set(FIELDS):
        return False
    report, fragment, effective, mount = (value[key] for key in FIELDS)
    return (isinstance(report, dict) and report.get('metadata_collected') is True
            and report.get('migration_ready') is False and report.get('reasons') == []
            and isinstance(fragment, dict) and fragment.get('outcome') == 'ok'
            and all(isinstance(record, dict) and record.get('collected') is True
                    and record.get('errors') == [] for record in (effective, mount)))


def differences(before, after):
    # JSON serialization distinguishes booleans from integers, unlike Python ==.
    return [key for key in FIELDS if json.dumps(before.get(key), sort_keys=True) !=
            json.dumps(after.get(key), sort_keys=True)]


def record(before, after):
    errors = []
    if not complete(before) or not complete(after):
        errors.append('Both observation passes must be complete and successful')
    errors.extend('Observation changed: ' + key for key in differences(before, after))
    return dict(schema=1, method='repeat-all-v1', after=after,
                agrees=not errors, errors=errors, limitations=LIMITATIONS)


def assess(evidence):
    value = evidence.get('coherence')
    if (not isinstance(value, dict) or set(value) !=
            {'schema', 'method', 'after', 'agrees', 'errors', 'limitations'} or
            type(value['schema']) is not int or value['schema'] != 1 or
            value['method'] != 'repeat-all-v1' or not isinstance(value['after'], dict)):
        return ['Capture coherence is missing or malformed']
    expected = record(observations(evidence), value['after'])
    if json.dumps(value, sort_keys=True) != json.dumps(expected, sort_keys=True):
        return ['Capture coherence derived fields disagree with observations']
    return expected['errors']
