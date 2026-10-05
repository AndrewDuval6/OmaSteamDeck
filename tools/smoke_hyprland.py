#!/usr/bin/env python3
"""Opt-in live compositor test. Touches only its own windows and two empty workspaces."""
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtTest import QTest
from omasteamdeck.desktop import Desktop

app=QApplication([])
desktop=Desktop()
if not desktop.available:
    raise SystemExit(desktop.reason)
original=desktop.query('activeworkspace')
focused=desktop.query('activewindow').get('address')
reserved={'9911','9912'}
assert not any(w['name'] in reserved for w in desktop.query('workspaces')), 'QA workspaces already in use; refusing to disturb them.'
windows=[]
try:
    desktop.focus_workspace('9911')
    for title in ('OmaSteamDeck','OSD integration test'):
        w=QLabel(title); w.setWindowTitle(title); w.resize(420,300); w.show(); windows.append(w)
    QTest.qWait(450)
    clients=[c for c in desktop.query('clients') if c.get('pid')==os.getpid()]
    assert len(clients)==2, 'Two native test windows must be mapped'
    first,second=[c['address'] for c in clients]
    for address in (first,second): desktop.tile(address)
    QTest.qWait(100)
    clients=[c for c in desktop.query('clients') if c.get('pid')==os.getpid()]
    assert all(not c['floating'] for c in clients), 'Both test windows must be tiled'
    assert clients[0]['at']!=clients[1]['at'], 'Tiled windows must have distinct positions'
    desktop.focus_window(first); QTest.qWait(100)
    assert desktop.query('activewindow')['address']==first
    desktop.toggle_float(first); QTest.qWait(100)
    assert next(c for c in desktop.query('clients') if c['address']==first)['floating']
    desktop.tile(first); desktop.move_window(second,'9912'); desktop.focus_workspace('9912'); QTest.qWait(100)
    assert desktop.query('activeworkspace')['name']=='9912'
    assert next(c for c in desktop.query('clients') if c['address']==second)['workspace']['name']=='9912'
    desktop.return_console(os.getpid()); QTest.qWait(100)
    assert desktop.query('activewindow')['title']=='OmaSteamDeck'
    print('PASS: native windows, tiling, floating, window focus, workspace switch/move, return to console.')
    print('Hyprland:',desktop.version,'Omarchy available:',desktop.omarchy)
finally:
    for w in windows: w.close()
    QTest.qWait(100)
    if focused:
        desktop.focus_window(focused)
    else:
        desktop.focus_workspace(str(original['id']))
