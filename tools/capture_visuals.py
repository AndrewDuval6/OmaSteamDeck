#!/usr/bin/env python3
"""Capture all Build 1 visual states using disposable profile data, offscreen."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from omasteamdeck.app import Shell,TABS
from omasteamdeck.core import State,MEDIA

output=Path(sys.argv[1]) if len(sys.argv)>1 else Path('work/visuals')
output.mkdir(parents=True,exist_ok=True)
app=QApplication([])
with tempfile.TemporaryDirectory() as temp:
    # No sample games or accounts are presented as installed/connected.
    with patch('omasteamdeck.app.discover_games',return_value=[]):
        shell=Shell(State(Path(temp)/'state.json'),windowed=True,skip_splash=True)
    shell.resize(1280,800)
    def capture(name):
        QTest.qWait(60)
        if not shell.grab().save(str(output/(name+'.png'))): raise RuntimeError(name)
    capture('profiles')
    shell.choose_profile(0)
    for tab in TABS:
        shell.set_tab(tab); capture(tab.lower())
    QTimer.singleShot(100,lambda:(app.activeModalWidget().grab().save(str(output/'media-details.png')),app.activeModalWidget().reject()))
    shell.details(MEDIA[0])
    # Offscreen Qt does not reactivate the parent after closing a modal as a
    # native compositor does; restore it before inspecting focused states.
    shell.activateWindow(); QTest.qWait(20)
    shell.state.data['profiles']=[{'name':'Player '+str(n+1),'favorites':[],'recent':[]} for n in range(8)]
    shell.state.data['profiles'][0]['name']='A very long profile name'
    shell.state.data['scale']=130; shell.apply_scale(); shell.show_profiles(); capture('profiles-eight-large')
    shell.choose_profile(0)
    for tab in TABS:
        shell.set_tab(tab); capture(tab.lower()+'-large')
    shell.state.data['scale']=100; shell.apply_scale(); shell.show_splash(); capture('startup')
    shell.finish_splash(); capture('startup-transition'); QTest.qWait(400)
    shell.close()
print(output)
