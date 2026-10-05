import unittest
from unittest.mock import patch
from omasteamdeck.controller import Controller

class FakeSDL:
    def __init__(self): self.buttons=set(); self.axis={}; self.devices=[100]; self.closed=[]
    def SDL_PumpEvents(self): pass
    def SDL_GameControllerUpdate(self): pass
    def SDL_NumJoysticks(self): return len(self.devices)
    def SDL_JoystickGetDeviceInstanceID(self,index): return self.devices[index]
    def SDL_IsGameController(self,index): return True
    def SDL_GameControllerOpen(self,index): return self.devices[index]
    def SDL_GameControllerGetAttached(self,h): return h in self.devices
    def SDL_GameControllerClose(self,h): self.closed.append(h)
    def SDL_GameControllerGetButton(self,h,b): return b in self.buttons
    def SDL_GameControllerGetAxis(self,h,a): return self.axis.get(a,0)
    def SDL_QuitSubSystem(self,f): pass

class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.pad=Controller.__new__(Controller); self.pad.lib=FakeSDL(); self.pad.handles={}; self.pad.held=set(); self.pad.repeat={}
    def test_accept_is_edge_triggered_but_directions_repeat(self):
        self.pad.lib.buttons={0,13}
        with patch('omasteamdeck.controller.time.monotonic',return_value=0): self.assertEqual(set(self.pad.poll()),{'accept','left'})
        with patch('omasteamdeck.controller.time.monotonic',return_value=.1): self.assertEqual(self.pad.poll(),[])
        with patch('omasteamdeck.controller.time.monotonic',return_value=.5): self.assertEqual(self.pad.poll(),['left'])
        self.pad.lib.buttons=set(); self.pad.poll(); self.pad.lib.buttons={0}; self.assertEqual(self.pad.poll(),['accept'])
    def test_unplug_reindex_and_reconnect(self):
        self.pad.lib.devices=[100,200]; self.pad.poll(); self.assertEqual(set(self.pad.handles),{100,200})
        self.pad.lib.devices=[200]; self.pad.poll(); self.assertEqual(set(self.pad.handles),{200}); self.assertEqual(self.pad.lib.closed,[100])
        self.pad.lib.devices=[200,300]; self.pad.poll(); self.assertEqual(set(self.pad.handles),{200,300})
    def test_deadzone_and_vertical_axis(self):
        self.pad.lib.axis={0:10000,1:-19000}; self.assertEqual(self.pad.poll(),['up'])
    def test_absent_sdl_is_graceful(self): self.pad.lib=None; self.assertEqual(self.pad.poll(),[]); self.pad.close()

class ChordTests(ControllerTests):
    def test_view_start_returns_without_settings_or_workspace_tap(self):
        self.pad.lib.buttons={4}; self.assertEqual(self.pad.poll(),[])
        self.pad.lib.buttons={4,6}; self.assertEqual(self.pad.poll(),['console'])
        self.assertEqual(self.pad.poll(),[])
        self.pad.lib.buttons=set(); self.assertEqual(self.pad.poll(),[])
    def test_view_tap_and_direction_chord(self):
        self.pad.lib.buttons={4}; self.pad.poll(); self.pad.lib.buttons=set(); self.assertEqual(self.pad.poll(),['workspaces'])
        self.pad.lib.buttons={4,13}; self.assertEqual(self.pad.poll(),['wm:left'])
        self.pad.lib.buttons=set(); self.assertEqual(self.pad.poll(),[])
    def test_release_modifier_first_does_not_leak_start_into_menu(self):
        self.pad.lib.buttons={4,6}; self.assertEqual(self.pad.poll(),['console'])
        self.pad.lib.buttons={6}; self.assertEqual(self.pad.poll(),[])
        self.assertEqual(self.pad.poll(),[])
        self.pad.lib.buttons=set(); self.pad.poll()
        self.pad.lib.buttons={6}; self.assertEqual(self.pad.poll(),['menu'])
    def test_release_start_first_does_not_leak_workspace_tap(self):
        self.pad.lib.buttons={4,6}; self.assertEqual(self.pad.poll(),['console'])
        self.pad.lib.buttons={4}; self.assertEqual(self.pad.poll(),[])
        self.pad.lib.buttons=set(); self.assertEqual(self.pad.poll(),[])
