#!/usr/bin/env python3
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader('restart', str(ROOT / 'src/bin/frankenstein-shell-restart'))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec); loader.exec_module(m)

class RestartTests(unittest.TestCase):
    def test_selection_never_duplicates(self):
        s = {'stock': {'LoadState':'loaded','ActiveState':'active'}, 'adapter': {'LoadState':'loaded','ActiveState':'inactive'}}
        self.assertEqual(m.choose(s), 'stock')
        s['stock']['ActiveState']='inactive'; s['adapter']['ActiveState']='active'
        self.assertEqual(m.choose(s), 'adapter')
        s['stock']['ActiveState']='active'
        with self.assertRaises(RuntimeError): m.choose(s)
        s['stock']['ActiveState']=s['adapter']['ActiveState']='inactive'
        with self.assertRaises(RuntimeError): m.choose(s)
        s['adapter']['LoadState']='not-found'
        self.assertEqual(m.choose(s), 'stock')

    def test_hyprland_delegates_to_original(self):
        with patch.dict(os.environ, {'XDG_CURRENT_DESKTOP':'Hyprland','XDG_SESSION_TYPE':'wayland'}), patch.object(m.os,'execv',side_effect=SystemExit) as execute:
            with self.assertRaises(SystemExit): m.restart()
            execute.assert_called_once_with('/usr/bin/omarchy-restart-shell',['/usr/bin/omarchy-restart-shell'])

    def test_kde_retries_ipc_and_uses_one_service(self):
        def query(unit): return {'LoadState':'loaded' if unit==m.SERVICES[0] else 'not-found','ActiveState':'active' if unit==m.SERVICES[0] else 'inactive'}
        responses=[subprocess.CompletedProcess([],0,''), subprocess.CompletedProcess([],1,''), subprocess.CompletedProcess([],0,'ok\n')]
        with patch.dict(os.environ, {'XDG_CURRENT_DESKTOP':'KDE','XDG_SESSION_TYPE':'wayland'}), patch.object(m,'query',side_effect=query), patch.object(m.subprocess,'run',side_effect=responses) as run, patch.object(m.time,'sleep'):
            m.restart()
            self.assertEqual(run.call_args_list[0].args[0],['systemctl','--user','restart',m.SERVICES[0]])
            self.assertEqual(run.call_args_list[-1].args[0],['omarchy-shell','shell','ping'])

    def test_shared_normalization_and_ambiguous_refusal(self):
        with patch.dict(os.environ, {'XDG_CURRENT_DESKTOP':'Other:KDE','XDG_SESSION_TYPE':'wayland'}), patch.object(m,'query',return_value={'LoadState':'not-found','ActiveState':'inactive'}):
            with self.assertRaisesRegex(RuntimeError, 'unambiguous'): m.restart()
        with patch.dict(os.environ, {'XDG_CURRENT_DESKTOP':'KDE:Hyprland'}), patch.object(m.os,'execv') as execute:
            with self.assertRaisesRegex(RuntimeError, 'provider'): m.restart()
            execute.assert_not_called()

    def test_user_wrapper_lifecycle_and_existing_command(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {'HOME':d,'XDG_STATE_HOME':d+'/state','XDG_CONFIG_HOME':d+'/config'}):
            m.install(); m.install()
            base=Path(d)/'.local/bin'
            self.assertIn('exec /usr/bin/omarchy "$@"',(base/'omarchy').read_text())
            m.remove(); self.assertFalse((base/'omarchy').exists())
            (base/'omarchy').write_text('#!/bin/sh\necho custom\n')
            with self.assertRaises(RuntimeError): m.install()
            self.assertIn('custom',(base/'omarchy').read_text())

if __name__=='__main__': unittest.main()
