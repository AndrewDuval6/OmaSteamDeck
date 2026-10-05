#!/usr/bin/env python3
"""Render reproducible 1280x800 QA images; does not read the user's profile state."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from omasteamdeck.app import Shell, TextDialog
from omasteamdeck.core import State, Item

output=Path(sys.argv[1]) if len(sys.argv)>1 else Path('work/screenshots')
output.mkdir(parents=True,exist_ok=True)
app=QApplication([])
with tempfile.TemporaryDirectory() as temp:
    shell=Shell(State(Path(temp)/'state.json'),windowed=True,skip_splash=True)
    shell.resize(1280,800)
    def capture(name):
        QTest.qWait(80); shell.grab().save(str(output/(name+'.png')))
    capture('profiles')
    shell.choose_profile(0)
    for tab in ('Games','Media','Store','Library','Apps','Settings'):
        shell.set_tab(tab); capture(tab.lower())
    shell.state.data['scale']=130; shell.apply_scale(); shell.set_tab('Settings'); capture('settings-large-text')
    shell.state.data['scale']=100; shell.apply_scale()
    shell.show_splash(); capture('startup')
    keyboard=TextDialog('Name your profile',parent=shell); keyboard.show(); QTest.qWait(50); keyboard.grab().save(str(output/'keyboard.png')); keyboard.close()
    shell.close()
print(output)
