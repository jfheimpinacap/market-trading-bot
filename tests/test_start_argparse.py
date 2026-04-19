from __future__ import annotations

import unittest
from types import SimpleNamespace
from pathlib import PureWindowsPath
from unittest import mock

import start


class StartParserGuiSilentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = start.build_parser()

    def test_gui_silent_before_subcommand_is_accepted(self) -> None:
        args = self.parser.parse_args(['--gui-silent', 'full'])
        self.assertTrue(args.gui_silent)
        self.assertEqual(args.command, 'full')

    def test_gui_silent_after_subcommand_is_accepted(self) -> None:
        args = self.parser.parse_args(['full', '--gui-silent'])
        self.assertTrue(args.gui_silent)
        self.assertEqual(args.command, 'full')

    def test_gui_silent_for_backend_and_frontend_subcommands(self) -> None:
        backend_args = self.parser.parse_args(['backend', '--gui-silent'])
        frontend_args = self.parser.parse_args(['frontend', '--gui-silent'])
        self.assertTrue(backend_args.gui_silent)
        self.assertTrue(frontend_args.gui_silent)


class StartStartupPreferenceTests(unittest.TestCase):
    def test_resolve_startup_preferences_silent_forces_single_console(self) -> None:
        args = SimpleNamespace(gui_silent=True, separate_windows=True, verbose=True)
        startup_mode, verbose_logs, gui_silent = start.resolve_startup_preferences(args, allow_verbose=True)
        self.assertEqual(startup_mode, start.DEFAULT_STARTUP_MODE)
        self.assertFalse(verbose_logs)
        self.assertTrue(gui_silent)

    def test_resolve_startup_preferences_debug_windows(self) -> None:
        args = SimpleNamespace(gui_silent=False, separate_windows=True, verbose=False)
        startup_mode, verbose_logs, gui_silent = start.resolve_startup_preferences(args, allow_verbose=True)
        self.assertEqual(startup_mode, 'separate-windows')
        self.assertFalse(verbose_logs)
        self.assertFalse(gui_silent)


class StartWindowsSilentSpawnTests(unittest.TestCase):
    @mock.patch('start.os.name', 'nt')
    def test_windows_no_window_kwargs_include_hidden_startupinfo(self) -> None:
        kwargs = start.windows_no_window_kwargs()
        self.assertEqual(kwargs['creationflags'], getattr(start.subprocess, 'CREATE_NO_WINDOW', 0))
        if 'startupinfo' in kwargs:
            startupinfo = kwargs['startupinfo']
            self.assertTrue(startupinfo.dwFlags & getattr(start.subprocess, 'STARTF_USESHOWWINDOW', 0))

    @mock.patch('start.os.name', 'nt')
    def test_frontend_command_uses_npm_cli_without_cmd_wrapper(self) -> None:
        npm_cmd = r'C:\Program Files\nodejs\npm.cmd'
        expected_cli = str(PureWindowsPath(r'C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js'))
        with (
            mock.patch('start.npm_exec', return_value=npm_cmd),
            mock.patch('start.node_exec', return_value=r'C:\Program Files\nodejs\node.exe'),
            mock.patch('start.os.path.exists', return_value=True),
        ):
            command = start.frontend_run_command()
        self.assertEqual(command[0], r'C:\Program Files\nodejs\node.exe')
        self.assertEqual(command[1], str(expected_cli))
        self.assertEqual(command[2:5], ['run', 'dev', '--'])


if __name__ == '__main__':
    unittest.main()
