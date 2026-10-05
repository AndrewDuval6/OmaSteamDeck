#!/usr/bin/env python3
"""Exercise native UI navigation using a real SDL virtual controller."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import ctypes as C
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from omasteamdeck.app import Shell
from omasteamdeck.core import State

app=QApplication([])
with tempfile.TemporaryDirectory() as temp:
    shell=Shell(State(Path(temp)/'state.json'),windowed=True,skip_splash=True)
    lib=shell.controller.lib
    if not lib: raise SystemExit('SDL2 unavailable')
    for name,args,result in [('SDL_JoystickAttachVirtual',[C.c_int,C.c_int,C.c_int,C.c_int],C.c_int),('SDL_JoystickDetachVirtual',[C.c_int],C.c_int),('SDL_JoystickOpen',[C.c_int],C.c_void_p),('SDL_JoystickClose',[C.c_void_p],None),('SDL_JoystickSetVirtualButton',[C.c_void_p,C.c_int,C.c_ubyte],C.c_int)]:
        function=getattr(lib,name); function.argtypes=args; function.restype=result
    index=lib.SDL_JoystickAttachVirtual(1,6,15,0)
    assert index>=0,'Could not create virtual controller'
    handle=lib.SDL_JoystickOpen(index)
    try:
        shell.activateWindow(); QTest.qWait(100)
        def press(button):
            assert lib.SDL_JoystickSetVirtualButton(handle,button,1)==0
            QTest.qWait(80)
            assert lib.SDL_JoystickSetVirtualButton(handle,button,0)==0
            QTest.qWait(80)
        assert shell.controller.handles,'Virtual controller did not connect'
        press(0); assert shell.page=='home','A did not choose profile'
        press(10); assert shell.tab=='Media','RB did not change section'
        press(14); assert app.focusWidget()==shell.cards[1],'D-pad did not move focus'
        press(2); assert shell.profile['favorites']==['spotify'],'X did not pin the selected item'
        press(1); assert shell.page=='profiles','B did not return to profiles'
        print('PASS: real SDL hotplug, A selection, RB section change, D-pad focus, X pin, B back.')
    finally:
        lib.SDL_JoystickClose(handle); lib.SDL_JoystickDetachVirtual(index); shell.close()
