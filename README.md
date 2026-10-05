# OmaFlow · Build 1 integration candidate

A native, controller-first Steam Deck handheld console with a real Omarchy + Hyprland desktop alongside it. Animated 3D startup, saved profiles, Home, Games, Media, Store, Library, Apps, Settings, tiled windows and workspaces.

The visible product name is **OmaFlow**; the repository, Python package, command
and existing config paths retain **OmaSteamDeck / omasteamdeck** identifiers.
The startup logo is a review concept. This candidate remains on
**`build1/integration`** pending review and physical Steam Deck acceptance.

**Build 1 targets Steam Deck handheld at 1280 × 800.** TV/docked optimization comes later. This repository does **not** partition disks, change bootloaders, install an OS, or rewrite desktop configuration.

## Run

The full experience requires an **existing Omarchy + Hyprland session on Steam Deck**, Python 3.10+, PySide6 and SDL2. Steam is required for Steam games; media/store links use the default browser. Stock SteamOS Gaming Mode does not provide the full desktop integration.

```bash
git clone --branch build1/integration https://github.com/AndrewDuval6/OmaSteamDeck.git
cd OmaSteamDeck
./run.sh
```

If PySide6 is not already available, install it locally in the checkout:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
./run.sh
```

No `sudo` is needed. SDL2 is loaded from the existing system; without it, keyboard/touch navigation remains available. Installing missing system/OS components is outside this build's installer scope.

Development and diagnostics:

```bash
./run.sh --windowed --skip-splash
./run.sh --config /tmp/omasteamdeck-test.json
python3 -m omasteamdeck.doctor
```

An optional desktop shortcut can be installed with `python3 tools/install_shortcut.py`; it writes only the user's applications directory and prints the path. Re-run if you move the checkout. It does not enable autostart or change login behavior.

## Controls

| Input | Action |
| --- | --- |
| D-pad / left stick / arrows | Move focus |
| A / Enter | Open / confirm |
| B / Esc | Back |
| X / F | Pin focused item |
| Y / `/` | Search with on-screen keyboard |
| LB / RB, Page Up / Down | Previous / next section |
| Start / F1 | Settings |
| View (Back) tap / F2 | Workspace and window picker |
| View + Start | Return to console from another app |
| View + D-pad | Focus a tiled window |
| View + LB / RB | Switch OSD workspaces |
| View + X | Tile the focused external window |
| View + Y | Move the focused external window to Desktop |
| F11 / Alt+F4 | Full screen / exit |

Use a **Gamepad** Steam Input template if launching through Steam. Avoid a simultaneous keyboard-emulation template that can send duplicate actions. SDL handles standard mapped controllers; actual Steam Deck input must pass the hardware checklist. External desktop apps use their own controls, including trackpads and touch.

## What is included

- Native Qt graphical shell, offline local navigation, perspective-projected animated monogram, reduced motion, text scaling, battery/time and controller status.
- Up to eight saved profiles, per-profile favorites and recent launch requests.
- Steam library discovery (including extra drives), visible desktop apps and exported Flatpaks; real launch actions.
- Media and store destinations open externally. Services handle login, playback, purchases and installation; the shell does not pretend to install packages.
- Hyprland's real tiling/floating windows and workspaces with version-aware dispatching. Omarchy Files, Terminal, system menu, sound and brightness controls.
- Automated tests, live compositor smoke test, development screenshots and CI.

[Integration handoff](docs/INTEGRATION.md) · [Build 1 specification](docs/BUILD1.md) · [Testing and hardware checklist](docs/TESTING.md) · [Product direction](docs/VISION.md)

The earlier web prototype is preserved in `index.html` and `src/`; it is not the native build. Build 1 implementation has been tested on a Linux Omarchy/Hyprland development host. **Physical Steam Deck acceptance is still required.**
