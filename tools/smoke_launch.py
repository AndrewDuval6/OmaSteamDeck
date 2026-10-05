#!/usr/bin/env python3
"""Opt-in live app-launch/tiling flow, using only disposable fixture windows."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtTest import QTest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from omasteamdeck.app import Shell
from omasteamdeck.core import State, discover_apps, MEDIA
from omasteamdeck.desktop import Desktop, WORKSPACES


def wait_for(callback, description, seconds=6):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        QTest.qWait(40)
        value = callback()
        if value:
            return value
    raise AssertionError(description)


def main():
    app = QApplication([])
    desktop = Desktop()
    if not desktop.available:
        raise SystemExit(desktop.reason)
    existing = desktop.query('clients')
    if any(c.get('workspace', {}).get('name') in WORKSPACES.values() for c in existing):
        raise SystemExit('OSD workspaces are in use; close their apps before this opt-in test.')
    original = desktop.query('activeworkspace')
    focused = desktop.query('activewindow').get('address')
    processes = []
    shell = None
    with tempfile.TemporaryDirectory(prefix='osd-launch-qa-') as directory:
        root = Path(directory)
        fixture = root / 'window.py'
        fixture.write_text('''import sys
from PySide6.QtWidgets import QApplication, QLabel
app = QApplication([])
window = QLabel(sys.argv[1])
window.setWindowTitle(sys.argv[1])
window.resize(420, 300)
window.show()
raise SystemExit(app.exec())
''')
        for number in (1, 2):
            (root / f'qa-{number}.desktop').write_text(
                '[Desktop Entry]\nType=Application\n'
                f'Name=OSD QA window {number}\n'
                f'Exec="{sys.executable}" "{fixture}" "OSD QA window {number}"\n')
        try:
            shell = Shell(State(root / 'state.json'), skip_splash=True)
            wait_for(lambda: shell.desktop_session_ready, 'Shell failed to attach to Hyprland')
            shell.choose_profile(0)
            QTest.qWait(50)
            shell.set_tab('Media')
            QTimer.singleShot(100, lambda: (shell.navigate('down'), shell.navigate('accept')))
            shell.details(MEDIA[0])
            wait_for(lambda: shell.isActiveWindow() and app.focusWidget(), 'Pinning from details lost native controller focus')
            assert app.focusWidget().item.id == MEDIA[0].id
            assert MEDIA[0].id in shell.profile['favorites']
            addresses = []
            for item in discover_apps([root]):
                # Use the same modal/controller route as selecting an Apps card.
                shell.desktop_control('console')
                QTimer.singleShot(100, lambda: shell.navigate('accept'))
                shell.details(item)
                wait_for(lambda: len(shell.children_processes) > len(processes), 'Details dialog did not request launch')
                process = shell.children_processes[-1]
                processes.append(process)
                client = wait_for(
                    lambda: next((c for c in desktop.query('clients') if c.get('pid') == process.pid), None),
                    'Launched native application did not map a window')
                assert client['workspace']['name'] == WORKSPACES['Desktop'], 'App opened on the wrong workspace'
                addresses.append(client['address'])
            assert len(shell.profile['recent']) == 2, 'Successful launches were not recorded'
            for address in addresses:
                desktop.tile(address)
            QTest.qWait(100)
            clients = [c for c in desktop.query('clients') if c['address'] in addresses]
            assert len(clients) == 2 and all(not c['floating'] for c in clients)
            assert clients[0]['at'] != clients[1]['at'], 'Native app windows did not tile separately'
            desktop.move_window(addresses[1], WORKSPACES['Play'])
            desktop.focus_window(addresses[1])
            QTest.qWait(80)
            assert desktop.query('activeworkspace')['name'] == WORKSPACES['Play']
            shell.desktop_control('wm:move')
            QTest.qWait(80)
            assert desktop.query('activeworkspace')['name'] == WORKSPACES['Desktop']
            shell.desktop_control('console')
            wait_for(lambda: desktop.query('activewindow').get('pid') == os.getpid(), 'Could not return to console')
            assert all(p.poll() is None for p in processes), 'Returning closed an external application'
            print('PASS: modal pin focus; two real native app launches through details; workspace, tiling, move, return and history.')
        finally:
            if shell is not None:
                shell.close()
            for process in processes:
                if process.poll() is None:
                    process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
            QTest.qWait(100)
            if focused:
                desktop.focus_window(focused)
            else:
                desktop.focus_workspace(str(original['id']))


if __name__ == '__main__':
    main()
