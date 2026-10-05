"""Presentation regressions at the handheld target, without external launches."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor,QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QLabel,QPushButton
from omasteamdeck.app import Shell,TABS
from omasteamdeck.core import State,MEDIA,Item
from omasteamdeck.visuals import Logo,ProfileCard,local_art

APP=QApplication.instance() or QApplication([])

class VisualTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        with patch('omasteamdeck.app.discover_games',return_value=[]),patch('omasteamdeck.app.discover_apps',return_value=[]):
            self.shell=Shell(State(self.root/'state.json'),windowed=True,skip_splash=True)
        self.shell.activateWindow(); QTest.qWait(10)
    def tearDown(self):
        self.shell.close(); self.shell.deleteLater(); APP.processEvents(); self.tmp.cleanup()
    def test_home_is_default_and_bumpers_reach_every_section(self):
        self.shell.navigate('accept'); self.assertEqual(self.shell.tab,'Home')
        visited=[]
        for _ in TABS:
            visited.append(self.shell.tab); self.shell.navigate('next')
        self.assertEqual(visited,TABS); self.assertEqual(self.shell.tab,'Home')
        self.shell.navigate('previous'); self.assertEqual(self.shell.tab,'Settings')
    def test_home_shortcuts_are_controller_accessible(self):
        self.shell.choose_profile(0); QTest.qWait(10)
        self.assertEqual(len(self.shell.cards),8)
        self.assertEqual(APP.focusWidget().title,'Play Games')
        self.shell.navigate('right'); self.shell.navigate('accept'); QTest.qWait(10); self.assertEqual(self.shell.tab,'Media')
        self.shell.navigate('left'); self.assertIs(APP.focusWidget(),self.shell.nav[TABS.index('Media')])
        self.shell.navigate('down'); self.assertEqual(APP.focusWidget().text(),'Store')
        self.shell.navigate('accept'); QTest.qWait(10); self.assertEqual(self.shell.tab,'Store')
        self.shell.navigate('left'); self.shell.navigate('right'); self.assertIs(APP.focusWidget(),self.shell.cards[0])
    def test_empty_shelves_offer_real_actions(self):
        self.shell.choose_profile(0); self.shell.set_tab('Games')
        self.assertEqual(self.shell.current_items,[]); self.assertEqual(len(self.shell.cards),4)
        with patch.object(self.shell,'launch') as launch:
            self.shell.cards[0].click(); self.assertEqual(launch.call_args.args[0].target,'steam://open/library')
        self.shell.set_tab('Library'); self.assertEqual(self.shell.current_items,[])
        self.shell.cards[0].click(); self.assertEqual(self.shell.tab,'Media')
    def test_home_search_and_saved_favorites_use_real_catalog(self):
        self.shell.profile['favorites']=['youtube']; self.shell.choose_profile(0)
        self.assertEqual([i.id for i in self.shell.current_items],['youtube'])
        self.shell.query='Spotify'; self.shell.show_home()
        self.assertEqual([i.id for i in self.shell.current_items],['spotify'])
    def test_eight_profiles_have_reachable_exit_and_scroll(self):
        self.shell.state.data['profiles']=[{'name':'Player '+str(i),'favorites':[],'recent':[]} for i in range(8)]
        self.shell.state.data['scale']=130; self.shell.apply_scale(); self.shell.show_profiles(); QTest.qWait(10)
        self.assertEqual(len(self.shell.findChildren(ProfileCard)),8)
        self.shell.navigate('down'); QTest.qWait(10)
        focus=APP.focusWidget(); self.assertEqual(focus.name,'Player 4')
        visible=self.shell.profile_scroll.viewport().rect()
        self.assertTrue(visible.contains(focus.mapTo(self.shell.profile_scroll.viewport(),focus.rect().center())))
        self.shell.navigate('down'); self.assertEqual(APP.focusWidget().text(),'Exit to desktop')
        self.shell.navigate('up'); self.assertIsInstance(APP.focusWidget(),ProfileCard)
    def test_native_icon_is_static_and_reduced_motion_has_no_fade(self):
        logo=Logo(True); logo.show(); QTest.qWait(10); self.assertTrue(logo.renderer.isValid())
        self.assertFalse(logo.timer.isActive()); logo.close()
        self.shell.state.data['motion']=False; self.shell.show_splash(); QTest.qWait(10)
        for widget in self.shell.findChildren(Logo):
            if widget.isVisible(): self.assertFalse(widget.timer.isActive())
        self.shell.finish_splash(); self.assertEqual(self.shell.page,'profiles'); self.assertFalse(hasattr(self.shell,'transition'))
    def test_splash_skip_fades_without_stealing_profile_input(self):
        self.shell.show_splash(); QTest.qWait(10); self.shell.finish_splash()
        self.assertEqual(self.shell.page,'profiles'); self.assertIsInstance(APP.focusWidget(),ProfileCard)
        self.assertTrue(self.shell.transition.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents))
        self.shell.navigate('accept'); self.assertEqual(self.shell.page,'home')
        self.shell.finish_splash(); self.assertEqual(self.shell.page,'home')
        deadline=time.monotonic()+2
        while time.monotonic()<deadline and any(w.isVisible() and w.graphicsEffect() for w in self.shell.findChildren(QLabel)):
            QTest.qWait(20)
        self.assertFalse(any(w.isVisible() and w.graphicsEffect() for w in self.shell.findChildren(QLabel)))
    def test_large_text_and_long_names_fit_deck(self):
        self.shell.profile['name']='A very long profile name'; self.shell.state.data['scale']=130; self.shell.apply_scale(); self.shell.choose_profile(0)
        for tab in TABS:
            self.shell.set_tab(tab); QTest.qWait(10)
            self.assertLessEqual(self.shell.minimumSizeHint().width(),1280)
            self.assertEqual(self.shell.width(),1280)
            self.assertGreater(self.shell.scroll.viewport().height(),220)
            self.assertLessEqual(self.shell.notice.geometry().bottom(),800)
            for button in self.shell.nav: self.assertGreaterEqual(button.height(),40)
    def test_cached_art_and_malformed_desktop_icon_fallback(self):
        desktop=self.root/'bad.desktop'; desktop.write_bytes(b'[Desktop Entry]\nIcon=\xff\n')
        self.assertTrue(local_art(Item('app:x','Broken','Test','app',str(desktop))).isNull())
        cache=self.root/'.local/share/Steam/appcache/librarycache'; cache.mkdir(parents=True)
        image=QImage(600,900,QImage.Format.Format_RGB32); image.fill(QColor('red')); image.save(str(cache/'42_library_600x900.jpg'))
        with patch('omasteamdeck.visuals.Path.home',return_value=self.root):
            art=local_art(Item('steam:42','Test','Installed','url','steam://rungameid/42'))
        self.assertFalse(art.isNull()); self.assertLessEqual(art.height(),400)

if __name__=='__main__': unittest.main()
