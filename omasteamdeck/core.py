"""Local catalog and durable, unprivileged profile storage."""
from __future__ import annotations
import configparser
import json
import os
from pathlib import Path
import re
import shlex
import shutil
from dataclasses import dataclass

@dataclass
class Item:
    id: str
    name: str
    subtitle: str
    kind: str
    target: str
    icon: str = '◈'

MEDIA = [Item('youtube', 'YouTube', 'Videos & live streams', 'url', 'https://www.youtube.com', '▶'), Item('spotify', 'Spotify', 'Music for every session', 'url', 'https://open.spotify.com', '♫'), Item('netflix', 'Netflix', 'Films & series · account required', 'url', 'https://www.netflix.com', 'N'), Item('prime', 'Prime Video', 'Movies · account required', 'url', 'https://www.primevideo.com', '▷')]
STORES = [Item('steam-store', 'Steam', 'Discover your next adventure', 'url', 'https://store.steampowered.com', '◎'), Item('flathub', 'Flathub', 'Explore Linux applications', 'url', 'https://flathub.org', '▦'), Item('gog', 'GOG', 'DRM-free games', 'url', 'https://www.gog.com', 'G'), Item('itch', 'itch.io', 'Independent games & creators', 'url', 'https://itch.io', '◆')]

def discover_apps(roots=None):
    roots = roots or [Path.home()/'.local/share/applications', Path('/usr/local/share/applications'), Path('/usr/share/applications'), Path.home()/'.local/share/flatpak/exports/share/applications', Path('/var/lib/flatpak/exports/share/applications')]
    result, seen = [], set()
    for root in roots:
        for path in sorted(root.glob('*.desktop')):
            if path.name in seen:
                continue
            seen.add(path.name)
            c = configparser.ConfigParser(interpolation=None, strict=False)
            try:
                c.read(path, encoding='utf-8')
                d = c['Desktop Entry']
                if d.get('Type') != 'Application' or any(d.get(k, '').lower() == 'true' for k in ('Hidden','NoDisplay','Terminal')) or not d.get('Exec'):
                    continue
                if d.get('TryExec') and not shutil.which(d['TryExec']):
                    continue
                result.append(Item('app:'+str(path), d.get('Name', path.stem), d.get('Comment', 'Installed application'), 'app', str(path)))
            except (OSError, configparser.Error, KeyError):
                continue
    return sorted(result, key=lambda x: x.name.lower())

def desktop_command(path):
    c = configparser.ConfigParser(interpolation=None, strict=False)
    c.read(path, encoding='utf-8')
    d = c['Desktop Entry']
    args = []
    for arg in shlex.split(d['Exec']):
        if arg == '%c': args.append(d.get('Name', ''))
        elif arg == '%k': args.append(str(path))
        elif arg == '%i':
            if d.get('Icon'): args.extend(['--icon', d['Icon']])
        elif arg not in ('%f','%F','%u','%U','%d','%D','%n','%N','%v','%m'):
            args.append(arg.replace('%%','%'))
    return args, d.get('Path') or None

def discover_games(home=None):
    home = home or Path.home()
    roots = [home/'.steam/steam', home/'.local/share/Steam', home/'.var/app/com.valvesoftware.Steam/.local/share/Steam']
    libraries = set()
    for root in roots:
        libraries.add(root/'steamapps')
        try:
            content = (root/'steamapps/libraryfolders.vdf').read_text()
            libraries.update(Path(p.replace('\\\\','\\'))/'steamapps' for p in re.findall(r'"path"\s+"([^"]+)"', content))
        except OSError: pass
    games = {}
    for library in sorted(libraries):
        for manifest in library.glob('appmanifest_*.acf'):
            try:
                fields = dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"', manifest.read_text()))
                appid, name = fields.get('appid',''), fields.get('name','')
                if appid.isdigit() and name:
                    games[appid] = Item('steam:'+appid, name, 'Installed · Steam', 'url', 'steam://rungameid/'+appid, '▶')
            except OSError: pass
    return sorted(games.values(), key=lambda x: x.name.lower())

class State:
    def __init__(self, path=None):
        self.path = path or Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config'))/'omasteamdeck/state.json'
        self.data = {'profiles':[{'name':'Player 1','favorites':[], 'recent':[]}], 'motion':True, 'fullscreen':True, 'scale':100}
        try:
            saved = json.loads(self.path.read_text())
            profiles = saved.get('profiles')
            if isinstance(profiles,list) and profiles:
                clean = []
                for p in profiles[:8]:
                    if isinstance(p,dict) and isinstance(p.get('name'),str) and p['name'].strip():
                        clean.append({'name':p['name'][:24], 'favorites':[v for v in (p.get('favorites') if isinstance(p.get('favorites'),list) else []) if isinstance(v,str)], 'recent':[v for v in (p.get('recent') if isinstance(p.get('recent'),list) else []) if isinstance(v,str)][:12]})
                if clean: self.data['profiles'] = clean
            for key in ('motion','fullscreen'):
                if isinstance(saved.get(key),bool): self.data[key] = saved[key]
            if saved.get('scale') in (100,115,130): self.data['scale'] = saved['scale']
        except (OSError, ValueError, TypeError, AttributeError): pass
    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix('.tmp')
        temp.write_text(json.dumps(self.data, indent=2))
        temp.replace(self.path)
    def add_profile(self, name):
        name = name.strip()[:24]
        if not name or any(p['name'].casefold()==name.casefold() for p in self.data['profiles']) or len(self.data['profiles'])>=8:
            return False
        self.data['profiles'].append({'name':name,'favorites':[],'recent':[]})
        self.save()
        return True
