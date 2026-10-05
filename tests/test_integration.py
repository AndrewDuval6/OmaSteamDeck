"""Acceptance flows across the UI, persisted profiles and native launch layer."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omasteamdeck.app import Shell, TABS, TextDialog
from omasteamdeck.core import Item, State, discover_apps, discover_games
from omasteamdeck.desktop import Desktop, WORKSPACES

APP = QApplication.instance() or QApplication([])


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state_path = self.root / 'state.json'
        self.shell = None

    def tearDown(self):
        if self.shell is not None:
            self.shell.close()
            self.shell.deleteLater()
        APP.processEvents()
        self.temp.cleanup()

    def start(self, splash=False):
        self.shell = Shell(State(self.state_path), windowed=True,
                           skip_splash=not splash, desktop=Desktop(enabled=False))
        QTest.qWait(20)
        return self.shell

    def test_startup_profile_and_every_section_using_navigation(self):
        shell = self.start(splash=True)
        self.assertEqual(shell.page, 'splash')
        shell.navigate('accept')
        QTest.qWait(20)
        self.assertEqual(shell.page, 'profiles')
        shell.navigate('accept')
        QTest.qWait(20)
        self.assertEqual(shell.page, 'home')
        visited = []
        for _ in TABS:
            visited.append(shell.tab)
            self.assertIn(APP.focusWidget(), shell.cards + shell.nav)
            shell.navigate('next')
            QTest.qWait(20)
        self.assertEqual(set(visited), set(TABS))
        self.assertEqual(shell.tab, visited[0])

    def test_pin_survives_restart_and_isolated_profile_switch(self):
        state = State(self.state_path)
        state.add_profile('Second player')
        shell = self.start()
        shell.choose_profile(0)
        shell.set_tab('Media')
        shell.navigate('favorite')
        pinned = shell.profile['favorites'][0]
        shell.choose_profile(1)
        shell.set_tab('Library')
        self.assertEqual(shell.current_items, [])
        shell.close()
        shell.deleteLater()
        APP.processEvents()
        shell = self.start()
        shell.choose_profile(0)
        shell.set_tab('Library')
        self.assertEqual([item.id for item in shell.current_items], [pinned])

    def test_controller_keyboard_creates_profile_without_typing(self):
        shell = self.start()
        failures = []

        def enter_name():
            try:
                dialog = APP.activeModalWidget()
                self.assertIsInstance(dialog, TextDialog)
                # Enter AB using only navigation, then reach the Done key.
                shell.navigate('accept')
                shell.navigate('right')
                shell.navigate('accept')
                for _ in range(5):
                    shell.navigate('down')
                self.assertEqual(dialog.focusWidget().text(), 'Done')
                shell.navigate('accept')
            except BaseException as exc:
                failures.append(exc)
                if APP.activeModalWidget():
                    APP.activeModalWidget().reject()

        QTimer.singleShot(20, enter_name)
        shell.add_profile()
        if failures:
            raise failures[0]
        self.assertEqual(shell.page, 'home')
        self.assertEqual(shell.profile['name'], 'AB')
        self.assertEqual(State(self.state_path).data['profiles'][1]['name'], 'AB')

    def test_max_profiles_can_reach_exit_with_controller(self):
        state = State(self.state_path)
        for number in range(2, 9):
            state.add_profile(f'Player {number}')
        shell = self.start()
        for _ in range(len(shell.rows) + 1):
            shell.navigate('down')
        self.assertEqual(APP.focusWidget().text(), 'Exit to desktop')

    def test_discovered_desktop_app_executes_and_records_history(self):
        marker = self.root / 'launched.txt'
        program = self.root / 'fixture.py'
        program.write_text('from pathlib import Path\nimport sys\nPath(sys.argv[1]).write_text("launched")\n')
        entry = self.root / 'qa.desktop'
        entry.write_text('[Desktop Entry]\nType=Application\nName=QA fixture\n'
                         f'Exec="{sys.executable}" "{program}" "{marker}"\n')
        item, = discover_apps([self.root])
        shell = self.start()
        shell.choose_profile(0)
        shell.launch(item)
        self.assertEqual(len(shell.children_processes), 1)
        self.assertEqual(shell.children_processes[0].wait(timeout=5), 0)
        self.assertEqual(marker.read_text(), 'launched')
        self.assertEqual(State(self.state_path).data['profiles'][0]['recent'], [item.id])

    def test_discovered_steam_game_routes_to_play_before_protocol_handoff(self):
        steamapps = self.root / '.local/share/Steam/steamapps'
        steamapps.mkdir(parents=True)
        (steamapps / 'appmanifest_123.acf').write_text('"AppState" { "appid" "123" "name" "QA Game" }')
        game, = discover_games(self.root)
        shell = self.start()
        shell.choose_profile(0)
        desktop = Mock(spec=Desktop)
        desktop.available = True
        shell.desktop = desktop
        shell.desktop_session_ready = True
        events = []
        desktop.focus_workspace.side_effect = lambda name: events.append(('workspace', name))
        with patch('omasteamdeck.app.QDesktopServices.openUrl',
                   side_effect=lambda url: events.append(('url', url.toString())) or True):
            shell.launch(game)
        self.assertEqual(events, [('workspace', WORKSPACES['Play']), ('url', 'steam://rungameid/123')])
        self.assertEqual(shell.profile['recent'], [game.id])

    def test_failed_native_launch_restores_console_without_history(self):
        entry = self.root / 'missing.desktop'
        entry.write_text('[Desktop Entry]\nType=Application\nName=Missing\nExec=/nonexistent/osd-qa-app\n')
        item = Item('missing', 'Missing', 'Launch failure fixture', 'app', str(entry))
        shell = self.start()
        shell.choose_profile(0)
        shell.desktop = Mock(spec=Desktop)
        shell.desktop.available = True
        shell.desktop_session_ready = True
        shell.launch(item)
        shell.desktop.return_console.assert_called_once_with(os.getpid())
        self.assertEqual(shell.profile['recent'], [])
        self.assertIn('Could not launch', shell.notice.text())

    def test_desktop_entry_changed_after_discovery_fails_gracefully(self):
        entry = self.root / 'changed.desktop'
        entry.write_text('[Desktop Entry]\nType=Application\nName=Changed\nExec=/bin/true\n')
        item, = discover_apps([self.root])
        shell = self.start()
        shell.choose_profile(0)
        entry.write_text('incomplete desktop entry during a package update')
        shell.launch(item)
        self.assertEqual(shell.profile['recent'], [])
        self.assertIn('Could not launch Changed', shell.notice.text())

    def test_large_library_scrolls_to_controller_focus_and_keeps_pin_focus(self):
        shell = self.start()
        shell.choose_profile(0)
        QTest.qWait(20)
        shell.games = [Item(f'steam:{number}', f'Game {number}', 'QA catalog',
                            'url', f'steam://rungameid/{number}') for number in range(45)]
        shell.set_tab('Games')
        QTest.qWait(30)
        for _ in range(11):
            shell.navigate('down')
            QTest.qWait(20)
        QTest.qWait(30)
        self.assertIs(APP.focusWidget(), shell.cards[-1])
        self.assertGreater(shell.scroll.verticalScrollBar().value(), 0)
        shell.navigate('favorite')
        QTest.qWait(30)
        self.assertEqual(APP.focusWidget().item.id, 'steam:44')
        focused = APP.focusWidget()
        visible = shell.scroll.viewport().rect()
        self.assertTrue(visible.contains(focused.mapTo(shell.scroll.viewport(), focused.rect().center())))


if __name__ == '__main__':
    unittest.main()
