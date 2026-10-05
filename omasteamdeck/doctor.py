"""Read-only target diagnostics; never installs or configures anything."""
import ctypes.util
import json
import os
from pathlib import Path
import shutil
from .desktop import Desktop

def main():
    desktop=Desktop()
    try: hardware=Path('/sys/class/dmi/id/product_name').read_text().strip()
    except OSError: hardware='Unknown'
    report={'hardware':hardware,'steam_deck_detected':hardware in ('Jupiter','Galileo'),'hyprland':desktop.version,'hyprland_available':desktop.available,'omarchy':desktop.omarchy,'sdl2':bool(ctypes.util.find_library('SDL2')),'steam':bool(shutil.which('steam') or shutil.which('flatpak') and (Path.home()/'.var/app/com.valvesoftware.Steam').exists()),'wayland':bool(os.environ.get('WAYLAND_DISPLAY')),'partition_or_boot_changes':False}
    try:
        from PySide6.QtCore import qVersion
        report['qt']=qVersion()
    except ImportError: report['qt']='Missing PySide6'
    print(json.dumps(report,indent=2))
    return 0 if desktop.available and desktop.omarchy and report['sdl2'] and report['qt']!='Missing PySide6' else 1

if __name__=='__main__': raise SystemExit(main())
