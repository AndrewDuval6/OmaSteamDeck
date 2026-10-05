import subprocess
import unittest
from unittest.mock import patch, Mock
from omasteamdeck.desktop import Desktop, DesktopError, omarchy_command

class DesktopTests(unittest.TestCase):
    def adapter(self,modern=True):
        d=Desktop(enabled=False); d.available=True; d.modern=modern; d.run=Mock(return_value='ok'); return d
    def test_modern_dispatches_are_targeted(self):
        d=self.adapter(); d.tile('0xabc'); d.move_window('0xabc','osd-desktop')
        calls=[' '.join(c.args) for c in d.run.call_args_list]
        self.assertIn('window="address:0xabc"',calls[0]); self.assertIn('internal=0',calls[0]); self.assertIn('action="off"',calls[1]); self.assertIn('workspace="name:osd-desktop"',calls[2]); self.assertIn('follow=false',calls[2])
    def test_legacy_dispatches(self):
        d=self.adapter(False); d.tile('0xabc')
        self.assertEqual(d.run.call_args_list[0].args,('dispatch','focuswindow','address:0xabc'))
        self.assertEqual(d.run.call_args_list[-1].args,('dispatch','settiled','address:0xabc'))
    def test_rejects_untrusted_dispatch_arguments(self):
        d=self.adapter()
        with self.assertRaises(DesktopError): d.focus_window('0xabc"}); malicious()')
        with self.assertRaises(DesktopError): d.focus_workspace('1; exec evil')
        d.run.assert_not_called()
    def test_return_console_uses_own_pid_and_title(self):
        for title in ('OmaHome','OmaSteamDeck'):
            with self.subTest(title=title):
                d=self.adapter()
                d.query=Mock(return_value=[{'address':'0xaaa','pid':4,'title':'Other'},{'address':'0xbbb','pid':5,'title':title},{'address':'0xccc','pid':4,'title':title}])
                d.return_console(4)
                self.assertIn('address:0xccc',d.run.call_args.args[1])
    def test_timeout_becomes_actionable_error(self):
        d=Desktop(enabled=False)
        with patch('omasteamdeck.desktop.subprocess.run',side_effect=subprocess.TimeoutExpired('hyprctl',2)):
            with self.assertRaisesRegex(DesktopError,'not responding'): d.query('clients')
    def test_omarchy_allowlist(self):
        with patch('omasteamdeck.desktop.shutil.which',return_value='/usr/bin/omarchy'):
            self.assertEqual(omarchy_command('volume-down'),['omarchy','audio','output','volume','-5'])
            with self.assertRaises(DesktopError): omarchy_command('system shutdown')
