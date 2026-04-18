from __future__ import annotations

import unittest

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


if __name__ == '__main__':
    unittest.main()
