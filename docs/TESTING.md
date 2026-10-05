# Build 1 verification

## Automated tests

```bash
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v
python3 -m compileall -q omasteamdeck tools
bash -n run.sh
```

Coverage includes profile persistence/isolation and corrupt state, native/extra Steam libraries, desktop entry visibility and arguments, all six pages, grid navigation, search/pinning, launch success/failure, keyboard entry, reduced motion, 1280 × 800 large text, modal focus isolation, controller hotplug/deadzones/repeat, both release orders of desktop chords, invalid catalog encoding, Hyprland version-specific commands, rejected invalid arguments, timeouts and allowlisted Omarchy actions. External launch behavior is mocked in unit tests; it is not proof of running a game or streaming playback.

## Live compositor smoke test (opt-in)

```bash
python3 tools/smoke_hyprland.py
```

Run inside Hyprland. Creates two temporary native windows, tests real tiled/floating placement, window focus, workspace changes and return-to-console, then closes only its own windows and restores the previously focused window. Refuses to run if its two QA workspaces (9911/9912) already exist. Does not edit persistent configuration.

## End-to-end input and native startup

```bash
python3 tools/smoke_input.py
python3 tools/smoke_shell.py
```

The input test uses an actual SDL virtual gamepad and polls the real native shell: device hotplug, profile selection, shoulder navigation, D-pad focus, pinning and Back. It is suitable for headless CI and does not claim to emulate Steam Deck hardware.

The shell test is opt-in and runs in the live Hyprland session with temporary profile data. It verifies full-screen startup, automatic profile transition, all sections, the modal workspace picker and return-to-console, then restores focus. It uses the shell's named OSD workspaces and never edits compositor configuration.

## Visual inspection

```bash
python3 tools/capture_ui.py /tmp/osd-screenshots
```

Captures the startup, profiles, all sections, on-screen keyboard and largest text mode at 1280 × 800 with isolated temporary profile data. App catalogs reflect installed software; no games or installations are fabricated for screenshots.

## Evidence from the development host

2026-10-04: 36 automated test cases passed (including repeated controller base cases), compile checks and launcher syntax passed. Actual Hyprland 0.56.2 / Omarchy 4.0.4-1 smoke test passed native tiling, floating, focus, window move, workspace switching and return-to-console. The real SDL virtual-controller test and full-screen native shell smoke test also passed. The baseline GitHub Actions workflow passed on Ubuntu/Python 3.12. Qt 6.11.2 renders were visually inspected at 1280 × 800. Existing compositor reports no configuration errors; no compositor config was modified.

The host is a ThinkPad, **not a Steam Deck**, and has no Steam client installed. This verifies code and real compositor integration; it does not certify the target device.

## Required Steam Deck acceptance (not yet performed)

- [ ] Fresh user-local dependency setup on an existing Deck Omarchy installation.
- [ ] Built-in controls through splash, profiles, all sections, search, text entry and modals.
- [ ] Steam Input gamepad mapping and global View + Start return with a running game.
- [ ] SDL controller reconnect; no double action or repeated launch on a held button.
- [ ] Launch a real installed Steam game and two native apps; tile/move/switch their windows.
- [ ] Browser media login, DRM playback where supported, and storefront handoff.
- [ ] Touch/trackpads, battery reporting, volume and display brightness.
- [ ] Suspend/resume and reconnect recovery.
- [ ] Handheld frame pacing, CPU load, thermals and battery runtime.
- [ ] Reboot existing OS, launch the shell again and verify profile persistence.

TV and docked tests are deliberately deferred beyond Build 1. Partition and bootloader work remains excluded.

## Startup runtime preflight

`python3 -m omasteamdeck.runtime` verifies Qt Widgets, Qt WebEngine, Qt WebChannel and the executable QtWebEngineProcess helper. It does not initialize a GUI or test WebGL; the startup view must verify real rendering separately. Missing system WebEngine libraries were correctly reported on this development host. `./run.sh --help` and explicit `--skip-splash` remain available for native-only diagnostics. The Three.js view is supplied by the separate UI integration.
