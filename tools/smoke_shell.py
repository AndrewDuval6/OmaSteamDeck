#!/usr/bin/env python3
"""Opt-in native shell test in the live compositor, with isolated profile data."""
import os
from pathlib import Path
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QPushButton
from PySide6.QtTest import QTest
from omasteamdeck.app import Shell, TABS
from omasteamdeck.core import State
from omasteamdeck.desktop import Desktop, WORKSPACES, CONSOLE_TITLES

app=QApplication([]); desktop=Desktop()
if not desktop.available: raise SystemExit(desktop.reason)
original=desktop.query('activeworkspace'); focus=desktop.query('activewindow').get('address')
with tempfile.TemporaryDirectory() as temp:
    shell=Shell(State(Path(temp)/'state.json'),windowed=False,skip_splash=False)
    try:
        deadline=time.monotonic()+8
        while time.monotonic()<deadline and not (shell.desktop_session_ready and shell.page=='profiles'):
            QTest.qWait(50)
        assert shell.desktop_session_ready,'Console failed to attach to Hyprland'
        assert shell.page=='profiles','Splash did not transition to profiles'
        assert desktop.query('activeworkspace')['name']==WORKSPACES['Console']
        shell.navigate('accept'); QTest.qWait(80); assert shell.page=='home'
        for tab in TABS:
            shell.set_tab(tab); QTest.qWait(30)
            assert app.focusWidget() in shell.cards+shell.nav,'Focus lost on '+tab
        def pick_desktop():
            dialog=app.activeModalWidget()
            assert dialog,'Workspace picker did not open'
            matches=[b for b in dialog.findChildren(QPushButton) if b.text().startswith('Desktop  ·')]
            assert matches; matches[0].click()
        QTimer.singleShot(80,pick_desktop); shell.workspaces(); QTest.qWait(150)
        assert desktop.query('activeworkspace')['name']==WORKSPACES['Desktop'],'Workspace picker failed to switch'
        shell.desktop_control('console'); QTest.qWait(100)
        assert desktop.query('activewindow')['title'] in CONSOLE_TITLES,'Return chord handler failed'
        print(f'PASS: actual full-screen shell, animated startup, profiles, {len(TABS)} sections, modal workspace picker, return-to-console.')
    finally:
        shell.close(); QTest.qWait(100)
        if focus: desktop.focus_window(focus)
        else: desktop.focus_workspace(str(original['id']))
