"""Runtime Hyprland + Omarchy integration. Never edits compositor or OS config."""
from __future__ import annotations
import json
import os
import re
import shutil
import subprocess

WORKSPACES = {'Console':'osd-console', 'Play':'osd-play', 'Media':'osd-media', 'Desktop':'osd-desktop'}

class DesktopError(RuntimeError): pass

class Desktop:
    def __init__(self, enabled=True):
        self.available=False; self.modern=False; self.version='Unavailable'; self.omarchy=bool(shutil.which('omarchy')); self.reason='Start in an Omarchy + Hyprland session to use workspaces.'
        if enabled and os.environ.get('HYPRLAND_INSTANCE_SIGNATURE') and shutil.which('hyprctl'):
            try:
                version=self.query('version'); self.version=version.get('version') or version.get('tag','')
                match=re.search(r'(\d+)\.(\d+)', self.version)
                self.modern=bool(match and tuple(map(int,match.groups())) >= (0,55))
                self.available=True; self.reason=''
            except DesktopError as exc: self.reason=str(exc)
    def run(self,*args):
        try:
            result=subprocess.run(['hyprctl',*args],capture_output=True,text=True,timeout=2,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc: raise DesktopError('Hyprland is not responding.') from exc
        text=result.stdout.strip()
        if result.returncode or text.lower().startswith(('error','invalid','unknown')):
            raise DesktopError((result.stderr.strip() or text or 'Hyprland action failed.')[:240])
        return text
    def query(self,name):
        try: return json.loads(self.run('-j',name))
        except ValueError as exc: raise DesktopError('Hyprland returned an unreadable response.') from exc
    def dispatch(self,modern,legacy,*args):
        if not self.available: raise DesktopError(self.reason)
        if self.modern: return self.run('dispatch',modern)
        return self.run('dispatch',legacy,*args)
    @staticmethod
    def address(value):
        if not re.fullmatch(r'0x[0-9a-fA-F]+',value): raise DesktopError('Invalid window address.')
        return 'address:'+value
    @staticmethod
    def workspace(value):
        if value in WORKSPACES.values(): return 'name:'+value
        if re.fullmatch(r'[1-9][0-9]*',value): return value
        raise DesktopError('Unknown workspace.')
    def focus_workspace(self,value):
        workspace=self.workspace(value)
        self.dispatch('hl.dsp.focus({workspace='+json.dumps(workspace)+'})','workspace',workspace)
    def focus_window(self,address):
        target=self.address(address)
        self.dispatch('hl.dsp.focus({window='+json.dumps(target)+'})','focuswindow',target)
    def move_window(self,address,workspace):
        target=self.address(address); dest=self.workspace(workspace)
        self.dispatch('hl.dsp.window.move({window='+json.dumps(target)+',workspace='+json.dumps(dest)+',follow=false})','movetoworkspacesilent',dest+','+target)
    def tile(self,address):
        target=self.address(address)
        # On old Hyprland fullscreenstate operates on the focused client only.
        if not self.modern: self.focus_window(address)
        self.dispatch('hl.dsp.window.fullscreen_state({window='+json.dumps(target)+',internal=0,client=0,action="set"})','fullscreenstate','0 0 set')
        self.dispatch('hl.dsp.window.float({window='+json.dumps(target)+',action="off"})','settiled',target)
    def toggle_float(self,address):
        target=self.address(address)
        self.dispatch('hl.dsp.window.float({window='+json.dumps(target)+',action="toggle"})','togglefloating',target)
    def focus_direction(self,direction):
        if direction not in ('l','r','u','d'): raise DesktopError('Invalid direction.')
        self.dispatch('hl.dsp.focus({direction='+json.dumps(direction)+'})','movefocus',direction)
    def cycle_workspace(self,delta):
        names=list(WORKSPACES.values()); current=self.query('activeworkspace').get('name')
        index=names.index(current) if current in names else 0
        self.focus_workspace(names[(index+delta)%len(names)])
    def shell_address(self,pid):
        return next((c['address'] for c in self.query('clients') if c.get('pid')==pid and c.get('title')=='OmaSteamDeck'),None)
    def return_console(self,pid):
        address=self.shell_address(pid)
        if not address: raise DesktopError('Console window is not available yet.')
        self.focus_window(address)
    def snapshot(self):
        if not self.available: raise DesktopError(self.reason)
        return self.query('workspaces'), self.query('clients')

# Only explicit, nonprivileged integrations can be launched from the UI.
OMARCHY_ACTIONS = {
    'files': ['launch','nautilus'],
    'terminal': ['launch','terminal'],
    'menu': ['menu','summon'],
    'volume-up': ['audio','output','volume','+5'],
    'volume-down': ['audio','output','volume','-5'],
    'mute': ['audio','output','volume','mute-toggle'],
    'brightness-up': ['brightness','display','+5%'],
    'brightness-down': ['brightness','display','5%-'],
}

def omarchy_command(action):
    if action not in OMARCHY_ACTIONS: raise DesktopError('Unknown Omarchy action.')
    if not shutil.which('omarchy'): raise DesktopError('Omarchy is not installed in this session.')
    return ['omarchy',*OMARCHY_ACTIONS[action]]
