#!/usr/bin/env python3
"""Opt-in native WebEngine smoke tests. Requires a working graphical session.

Uses disposable state and disables the Desktop adapter. No external launches.
Run separately from offscreen unit tests with a complete PySide6 installation.
"""
import json
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app=QApplication([])
app.setQuitOnLastWindowClosed(False)
from omasteamdeck.app import Shell,TextDialog
from omasteamdeck.core import State
from omasteamdeck.desktop import Desktop

def until(predicate,seconds=8):
    deadline=time.monotonic()+seconds
    while not predicate() and time.monotonic()<deadline: QTest.qWait(10)
    assert predicate(),'Timed out waiting for startup state'

def javascript(startup,expression):
    values=[]
    startup.page.runJavaScript(expression,values.append)
    until(lambda:bool(values))
    return values[0]

def restored(shell):
    until(lambda:shell.page=='profiles')
    QTest.qWait(400)
    margins=shell.root.contentsMargins()
    assert (margins.left(),margins.top(),margins.right(),margins.bottom())==(34,28,34,20)
    shell.activateWindow()
    shell.choose_profile(0)
    QTest.qWait(30)
    # Core app-wide key handling must be restored after WebEngine teardown.
    QTest.keyClick(shell,Qt.Key.Key_F1)
    assert shell.tab=='Settings'
    dialog=TextDialog('Input restoration',parent=shell)
    dialog.show();dialog.activateWindow();QTest.qWait(20)
    QTest.keyClicks(dialog,'Flow')
    assert dialog.edit.text()=='Flow'
    QTest.keyClick(dialog,Qt.Key.Key_Escape)
    assert not dialog.isVisible()
    dialog.deleteLater()

def close(shell):
    shell.close();shell.deleteLater();QTest.qWait(100)

with tempfile.TemporaryDirectory(prefix='omaflow-startup-test-') as temp:
    def create(motion=True):
        state=State(Path(temp)/'state.json');state.data['motion']=motion
        with patch('omasteamdeck.app.discover_games',return_value=[]),patch('omasteamdeck.app.discover_apps',return_value=[]):
            shell=Shell(state,windowed=True,desktop=Desktop(enabled=False))
        assert shell.startup is not None,'Run with WebEngine, not the native-only offscreen fixture'
        errors=[];shell.startup.failed.connect(errors.append)
        return shell,shell.startup,errors

    shell,startup,errors=create()
    until(lambda:startup.scene_ready)
    status=json.loads(javascript(startup,'JSON.stringify(window.omaflowStatus)'))
    assert status['renderer']=='three-webgl' and status['drawCalls']==2
    assert 0<status['triangles']<10000 and status['error'] is None
    restored(shell)
    assert startup.disposed and not errors,errors
    close(shell)
    print('PASS real native WebGL, automatic handoff, disposal and native/modal keys',status,flush=True)

    for key in (Qt.Key.Key_Return,Qt.Key.Key_Escape):
        shell,startup,errors=create();until(lambda:startup.scene_ready)
        # Send the key into the actual web focus surface.
        QTest.keyClick(startup.view.focusProxy() or startup.view,key)
        restored(shell);assert startup.disposed and not errors,errors;close(shell)
    print('PASS Enter/Escape skip and input restoration',flush=True)

    for action in ('accept','back'):
        shell,startup,errors=create()
        with patch.object(shell.controller,'poll',return_value=[action]),patch.object(shell,'isActiveWindow',return_value=True):shell.poll()
        restored(shell);assert startup.disposed;close(shell)
    print('PASS controller A/B actions before first frame',flush=True)

    shell,startup,errors=create(False);until(lambda:startup.scene_ready)
    assert javascript(startup,"document.body.classList.contains('reduced')")
    restored(shell);assert not getattr(shell,'transition',None) and not errors,errors;close(shell)
    print('PASS reduced motion',flush=True)

    shell,startup,errors=create();close(shell)
    shell,startup,errors=create();until(lambda:startup.scene_ready)
    shell.navigate('accept');restored(shell);assert not errors,errors;close(shell)
    print('PASS close while loading and fresh startup',flush=True)
