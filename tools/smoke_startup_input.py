#!/usr/bin/env python3
"""Opt-in real SDL/WebGL handoff and duplicate-launch checks.

Use a complete PySide6 runtime in a graphical session. --package-root verifies a
wheel installed outside the repository, including its actual offline WebGL scene.
Only temporary profile data and this test's windows/processes are used.
"""
import argparse
import ctypes as C
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--package-root', type=Path)
args = parser.parse_args()
module_root = (args.package_root or Path(__file__).resolve().parents[1]).resolve()
sys.path.insert(0, str(module_root))
import omasteamdeck
assert Path(omasteamdeck.__file__).resolve().is_relative_to(module_root)
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app = QApplication([])
app.setQuitOnLastWindowClosed(False)
from omasteamdeck.app import Shell, TextDialog
from omasteamdeck.core import State
from omasteamdeck.desktop import Desktop


def until(predicate, message, seconds=10):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        QTest.qWait(20)
        result = predicate()
        if result:
            return result
    raise AssertionError(message)


class VirtualPad:
    def __init__(self, shell):
        self.shell = shell
        lib = shell.controller.lib
        assert lib is not None, 'SDL2 is required for the real input check'
        self.lib = lib
        for name, params, result in [
            ('SDL_JoystickAttachVirtual', [C.c_int, C.c_int, C.c_int, C.c_int], C.c_int),
            ('SDL_JoystickDetachVirtual', [C.c_int], C.c_int),
            ('SDL_JoystickOpen', [C.c_int], C.c_void_p),
            ('SDL_JoystickClose', [C.c_void_p], None),
            ('SDL_JoystickSetVirtualButton', [C.c_void_p, C.c_int, C.c_ubyte], C.c_int),
        ]:
            function = getattr(lib, name)
            function.argtypes = params
            function.restype = result
        self.index = lib.SDL_JoystickAttachVirtual(1, 6, 15, 0)
        assert self.index >= 0, 'Virtual controller could not attach'
        self.handle = lib.SDL_JoystickOpen(self.index)
        assert self.handle, 'Virtual controller could not open'

    def press(self, button):
        action = {0: 'accept', 1: 'back', 10: 'next'}[button]
        modal = QApplication.activeModalWidget()
        assert self.shell.isActiveWindow() or (modal and modal.isActiveWindow()), (
            'QA window lost desktop focus; run native tests without concurrent previews or desktop interaction')
        assert self.lib.SDL_JoystickSetVirtualButton(self.handle, button, 1) == 0
        try:
            until(lambda: action in self.shell.controller.held, 'SDL did not sample the button press', seconds=2)
        finally:
            assert self.lib.SDL_JoystickSetVirtualButton(self.handle, button, 0) == 0
        until(lambda: action not in self.shell.controller.held, 'SDL did not sample the button release', seconds=2)

    def close(self):
        self.lib.SDL_JoystickClose(self.handle)
        self.lib.SDL_JoystickDetachVirtual(self.index)


desktop = Desktop()
previous = desktop.query('activewindow').get('address') if desktop.available else None
try:
    with tempfile.TemporaryDirectory(prefix='omaflow-input-qa-') as directory:
        root = Path(directory)
        for button in (0, 1):
            shell = None
            pad = None
            try:
                with patch('omasteamdeck.app.discover_apps', return_value=[]), patch('omasteamdeck.app.discover_games', return_value=[]):
                    shell = Shell(State(root / f'pad-{button}.json'), windowed=True, desktop=Desktop(enabled=False))
                startup = shell.startup
                assert startup is not None, 'This check requires the real WebEngine surface'
                errors = []
                startup.failed.connect(errors.append)
                pad = VirtualPad(shell)
                until(lambda: startup.scene_ready, 'Real Three.js scene did not render')
                values = []
                startup.page.runJavaScript('JSON.stringify(window.omaflowStatus)', values.append)
                until(lambda: values, 'Scene diagnostics did not respond')
                status = json.loads(values[0])
                assert status['renderer'] == 'three-webgl' and status['triangles'] > 0 and not status['error'], status
                until(lambda: shell.controller.handles, 'SDL did not detect the virtual controller')
                shell.activateWindow()
                QTest.qWait(30)
                pad.press(button)
                until(lambda: shell.page == 'profiles', 'SDL A/B did not leave the startup scene')
                QTest.qWait(400)
                assert startup.disposed and not errors, errors
                assert shell.root.contentsMargins().left() == 34, 'Native margins were not restored'
                pad.press(0)
                assert shell.page == 'home', 'SDL A did not select the profile after WebEngine disposal'
                pad.press(10)
                assert shell.tab == 'Games', 'SDL bumper input was not restored'
                QTest.keyClick(shell, Qt.Key.Key_F1)
                assert shell.tab == 'Settings', 'Native keyboard filter was not restored'
                dialog = TextDialog('Controller modal', parent=shell)
                dialog.show()
                dialog.activateWindow()
                until(dialog.isActiveWindow, 'Modal did not acquire native focus')
                pad.press(0)
                assert dialog.edit.text() == 'A', 'SDL modal keyboard activation failed'
                pad.press(1)
                assert not dialog.isVisible(), 'SDL B did not close the modal'
                dialog.deleteLater()
                print(f'PASS: real SDL {"A" if button == 0 else "B"} from WebGL to profiles, native input and modal input; {status["triangles"]} triangles.', flush=True)
            finally:
                if pad is not None:
                    pad.close()
                if shell is not None:
                    shell.close()
                    shell.deleteLater()
                QTest.qWait(150)

        # Exercise the real main/lock entry point with the WebEngine startup on.
        config = root / 'singleton.json'
        command = [sys.executable, '-m', 'omasteamdeck.app', '--windowed', '--config', str(config)]
        environment = dict(os.environ, PYTHONPATH=str(module_root))
        first = subprocess.Popen(command, cwd=root, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            until(lambda: config.with_suffix('.lock').exists() or first.poll() is not None, 'Initial process did not acquire its lock')
            assert first.poll() is None, 'First process exited during startup'
            if desktop.available:
                until(lambda: desktop.shell_address(first.pid), 'First process did not map its native window')
            QTest.qWait(500)
            second = subprocess.run(command, cwd=root, env=environment, capture_output=True, text=True, timeout=15)
            assert second.returncode == (0 if desktop.available else 1), second.stderr
            assert first.poll() is None, 'Duplicate launch disturbed the running process'
            if desktop.available:
                assert len([c for c in desktop.query('clients') if c.get('pid') == first.pid]) == 1
            print('PASS: second launch preserves the running WebEngine/native shell and its profile lock.', flush=True)
        finally:
            if first.poll() is None:
                first.terminate()
            try:
                first.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                first.kill()
                first.communicate(timeout=5)
finally:
    if previous and any(c.get('address') == previous for c in desktop.query('clients')):
        desktop.focus_window(previous)
