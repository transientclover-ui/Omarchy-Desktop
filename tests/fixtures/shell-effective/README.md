# Synthetic effective properties

`synthetic.json` is authored test data, not a VM capture or a claim that the
retained service's effective settings have been measured. Explicit values match
the 14-line retained unit in `../shell-metadata/fragment-261/`; implicit user
service dependencies and default settings implement the bounded candidate
contract documented in `docs/SHELL-OWNERSHIP.md`.

The fixture uses busctl JSON property records (`type` and `data`), including
empty structured arrays, integer microsecond durations and unsigned-64 infinity.
Identity paths, command PID and condition status are illustrative. Tests combine
this fixture with copies of the historical capture; they never overwrite that
capture or its exact fragment bytes. Do not register this as graphical or live
manager evidence.

The tests mutate every property independently, exercise malformed/missing data,
unknown fields, environment files, execution flags, query errors and stale or
conflicting observations. No environment file, captured command or source path
is opened or executed. Full typed property serialization and actual guest defaults
remain to be validated in a disposable VM.
