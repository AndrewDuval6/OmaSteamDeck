import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication, QPushButton
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from omasteamdeck.app import Shell, TABS, TextDialog, Logo
from omasteamdeck.core import State, MEDIA, Item

APP=QApplication.instance() or QApplication([])
class UiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.shell=Shell(State(Path(self.tmp.name)/'state.json'),windowed=True,skip_splash=True)
        QTest.qWait(20)
    def tearDown(self): self.shell.close(); APP.processEvents(); self.tmp.cleanup()
    def test_profile_selection_and_all_sections(self):
        self.shell.navigate('accept'); QTest.qWait(20)
        self.assertEqual(self.shell.page,'home')
        for tab in TABS:
            self.shell.set_tab(tab); QTest.qWait(20)
            self.assertEqual(self.shell.tab,tab)
            self.assertIn(APP.focusWidget(),self.shell.cards+self.shell.nav)
            self.assertGreater(self.shell.scroll.height(),100)
    def test_grid_and_back_navigation(self):
        self.shell.choose_profile(0); self.shell.set_tab('Media'); QTest.qWait(20)
        self.shell.navigate('right'); self.assertIs(APP.focusWidget(),self.shell.cards[1])
        self.shell.navigate('up'); self.assertIn(APP.focusWidget(),self.shell.rows[2])
        self.shell.navigate('down'); self.assertIs(APP.focusWidget(),self.shell.cards[0])
        self.shell.navigate('next'); self.assertEqual(self.shell.tab,'Store')
        self.shell.navigate('back'); self.assertEqual(self.shell.page,'profiles')
    def test_pin_library_and_search_empty_state(self):
        self.shell.choose_profile(0); self.shell.set_tab('Media'); QTest.qWait(20)
        self.shell.favorite(MEDIA[0]); self.shell.set_tab('Library')
        self.assertEqual([i.id for i in self.shell.current_items],['youtube'])
        self.shell.query='no match'; self.shell.show_home(); self.assertEqual(self.shell.current_items,[])
        self.shell.empty_action(); self.assertEqual(self.shell.query,'')
    def test_launch_success_and_failure_history(self):
        self.shell.choose_profile(0)
        with patch('omasteamdeck.app.QDesktopServices.openUrl',return_value=True) as open_url:
            self.shell.launch(MEDIA[0]); open_url.assert_called_once()
        self.assertEqual(self.shell.profile['recent'],['youtube'])
        with patch('omasteamdeck.app.QDesktopServices.openUrl',return_value=False): self.shell.launch(MEDIA[1])
        self.assertEqual(self.shell.profile['recent'],['youtube'])
        self.assertIn('No application',self.shell.notice.text())
    def test_settings_persist_and_stop_motion(self):
        self.shell.choose_profile(0); self.shell.set_tab('Settings'); self.shell.toggle_motion(); QTest.qWait(20)
        active=[l for l in self.shell.findChildren(Logo) if l.isVisible()]
        self.assertTrue(active); self.assertFalse(active[0].timer.isActive())
        self.shell.toggle_scale(); self.assertEqual(State(self.shell.state.path).data['scale'],115)
    def test_onscreen_keyboard_controller_and_typing(self):
        d=TextDialog('Name your profile',parent=self.shell); d.show(); QTest.qWait(20)
        d.navigate('accept'); d.navigate('right'); d.navigate('accept'); self.assertEqual(d.edit.text(),'AB')
        QTest.keyClicks(d,'sam'); self.assertEqual(d.edit.text(),'ABsam')
        d.navigate('back'); self.assertFalse(d.isVisible())
    def test_handheld_large_text(self):
        self.shell.choose_profile(0); self.shell.resize(1280,800); self.shell.state.data['scale']=130; self.shell.apply_scale()
        for tab in TABS:
            self.shell.set_tab(tab); QTest.qWait(10)
            self.assertLessEqual(self.shell.minimumSizeHint().width(),1280)
            self.assertGreater(self.shell.scroll.height(),100)
    def test_controller_dialog_does_not_activate_background(self):
        self.shell.choose_profile(0); self.shell.set_tab('Media')
        def check():
            self.assertIsNotNone(APP.activeModalWidget()); self.shell.navigate('back')
        QTimer.singleShot(20,check); self.shell.details(MEDIA[0]); self.assertEqual(self.shell.profile['recent'],[])

if __name__=='__main__': unittest.main()
