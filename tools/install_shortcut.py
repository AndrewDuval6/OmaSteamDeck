#!/usr/bin/env python3
"""Install one user-local shortcut; never edits Hyprland, autostart or OS files."""
import os
from pathlib import Path

def install(root=None,destination=None):
    root=root or Path(__file__).resolve().parents[1]
    destination=destination or Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))/'applications/omasteamdeck.desktop'
    # Desktop-entry Exec escaping differs from shell escaping.
    command=str(root/'run.sh').replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$').replace('%','%%')
    text='[Desktop Entry]\nType=Application\nName=OmaSteamDeck\nComment=Native Steam Deck console and Omarchy desktop\nExec="'+command+'"\nIcon=applications-games\nTerminal=false\nCategories=Game;\n'
    destination.parent.mkdir(parents=True,exist_ok=True); destination.write_text(text)
    return destination

if __name__=='__main__': print(install())
