"""Optional SDL2 controller polling, including hotplug and held-direction repeat."""
import ctypes as C
import ctypes.util
import time

class Controller:
    def __init__(self):
        self.lib = None
        self.handles = {}
        self.held = set()
        self.repeat = {}
        self.chord_used = False
        try:
            self.lib = C.CDLL(ctypes.util.find_library('SDL2') or 'libSDL2.so')
            for name,args,result in [('SDL_SetHint',[C.c_char_p,C.c_char_p],C.c_int),('SDL_InitSubSystem',[C.c_uint],C.c_int),('SDL_PumpEvents',[],None),('SDL_JoystickGetDeviceInstanceID',[C.c_int],C.c_int),('SDL_NumJoysticks',[],C.c_int),('SDL_IsGameController',[C.c_int],C.c_int),('SDL_GameControllerOpen',[C.c_int],C.c_void_p),('SDL_GameControllerGetAttached',[C.c_void_p],C.c_int),('SDL_GameControllerGetButton',[C.c_void_p,C.c_int],C.c_ubyte),('SDL_GameControllerGetAxis',[C.c_void_p,C.c_int],C.c_short),('SDL_GameControllerClose',[C.c_void_p],None),('SDL_GameControllerUpdate',[],None),('SDL_QuitSubSystem',[C.c_uint],None)]:
                fn = getattr(self.lib,name); fn.argtypes=args; fn.restype=result
            self.lib.SDL_SetHint(b'SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS',b'1')
            if self.lib.SDL_InitSubSystem(0x2000) != 0: self.lib = None
        except (OSError,AttributeError): self.lib = None
    def poll(self):
        if not self.lib: return []
        lib = self.lib
        lib.SDL_PumpEvents()
        lib.SDL_GameControllerUpdate()
        for index,handle in list(self.handles.items()):
            if not lib.SDL_GameControllerGetAttached(handle):
                lib.SDL_GameControllerClose(handle); del self.handles[index]
        for index in range(lib.SDL_NumJoysticks()):
            instance=lib.SDL_JoystickGetDeviceInstanceID(index)
            if instance not in self.handles and lib.SDL_IsGameController(index):
                handle=lib.SDL_GameControllerOpen(index)
                if handle: self.handles[instance]=handle
        active=set()
        for h in self.handles.values():
            for button,action in {0:'accept',1:'back',2:'favorite',3:'search',4:'modifier',5:'console',6:'menu',9:'previous',10:'next',11:'up',12:'down',13:'left',14:'right'}.items():
                if lib.SDL_GameControllerGetButton(h,button): active.add(action)
            for axis,negative,positive in [(0,'left','right'),(1,'up','down')]:
                value=lib.SDL_GameControllerGetAxis(h,axis)
                if value < -18000: active.add(negative)
                if value > 18000: active.add(positive)
        # Holding View/Back is a desktop modifier; its ordinary tap opens workspaces.
        if 'modifier' in active:
            chords={'menu':'console','left':'wm:left','right':'wm:right','up':'wm:up','down':'wm:down','previous':'wm:previous','next':'wm:next','favorite':'wm:tile','search':'wm:move'}
            combo={mapped for original,mapped in chords.items() if original in active}
            if combo: self.chord_used=True
            active=combo|{'modifier'}
        released_modifier='modifier' in self.held and 'modifier' not in active
        now=time.monotonic(); events=[]
        if released_modifier:
            if not getattr(self,'chord_used',False): events.append('workspaces')
            self.chord_used=False
        for action in active:
            if action=='modifier': continue
            if action not in self.held:
                events.append(action); self.repeat[action]=now+.4
            elif action in ('up','down','left','right') and now>=self.repeat.get(action,0):
                events.append(action); self.repeat[action]=now+.14
        self.held=active
        return events
    def close(self):
        if self.lib:
            for h in self.handles.values(): self.lib.SDL_GameControllerClose(h)
            self.handles.clear()
            self.lib.SDL_QuitSubSystem(0x2000)
            self.lib=None
