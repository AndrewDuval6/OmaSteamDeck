# Build 1 integration handoff

The review branch is **`build1/integration`**. Do not merge it into `main` until
the combined build is reviewed and the physical Steam Deck acceptance checklist
is completed. Development-host checks do not establish hardware acceptance.

## Source branches

- Core: `aef594b` — native shell, SDL controls, Hyprland/Omarchy integration,
  discovery and launch, lifecycle hardening and native smoke tests.
- UI: `58cdda3`, including `824c6b9` — reference-based handheld layout,
  OmaFlow display name, readable wrapped titles and provisional startup symbol.

Both workers' histories are retained. Integration fixes are limited to the
combined experience and its verification.

The visible product name is **OmaFlow**. The startup symbol remains a temporary
review preview while the UI task develops the standalone flow/interconnection
direction; no final logo approval is implied by this runnable checkpoint.
Repository, package, command and saved-data paths are unchanged. Core accepts
OmaFlow and the earlier window titles while matching the shell's own process,
preserving return-to-console behavior across the branding changes.

## Integration fixes

- Keep the selected card visible after pinning an item far down a library.
  Scroll restoration now waits for the rebuilt page's layout to settle.
- Recover gracefully when a desktop entry becomes malformed after catalog
  discovery, including returning from the destination workspace on failure.
- Check the packaged application outside the repository, so source-checkout
  imports cannot mask missing package contents.

## Verification

The integration suite exercises startup and profile selection, every section,
controller-only profile naming, persistence and profile isolation, eight-profile
navigation, long-library scrolling and pinning, a real local fixture application
launch, Steam protocol/workspace routing, and launch-failure recovery.

The runtime suite starts separate app processes to check single-instance
protection and recovery from a stale lock after an interrupted session.

The Steam protocol test verifies the handoff request. It does not launch a real
Steam game. The real application fixture is a small local subprocess; it does not
stand in for game, browser, or DRM testing.

On the development host (ThinkPad, Hyprland 0.56.2, Qt 6.11.2), the combined
baseline passes 51 automated cases and these additional checks:

- Real SDL virtual-controller input through profile selection, all seven
  sections, D-pad focus, pin and back.
- Live full-screen startup, profile transition, all sections, modal workspace
  selection and return-to-console.
- Pinning through a real native detail modal, followed by intact controller
  focus; two real GUI applications launched through detail dialogs, correct
  workspace placement, tiling, window movement, retained external processes
  and recorded launch history.
- Independent compositor smoke for tiling, floating, focus and workspaces.
- Wheel installation outside the repository, bundled PNG loading and rendering
  every section from the installed package.
- Visual inspection at 1280 × 800, including large text, eight profiles and
  detail dialogs. The capture harness explicitly restores offscreen focus after
  its modal screenshot; live compositor focus was separately verified.

See [TESTING.md](TESTING.md) for commands and the physical acceptance checklist.

## Test this branch on the handheld

Use the existing Omarchy/Hyprland installation on the Steam Deck:

```bash
git clone --branch build1/integration https://github.com/AndrewDuval6/OmaSteamDeck.git
cd OmaSteamDeck
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m omasteamdeck.doctor
./run.sh
```

The doctor command reports available components; read the individual values,
especially `steam_deck_detected`, `steam`, `sdl2`, `hyprland_available` and
`omarchy`. Its exit status alone is not a hardware acceptance result. SDL2 and
the existing OS components must already be available. No partition, bootloader
or persistent compositor configuration changes are part of this setup.

Record the exact commit (`git rev-parse HEAD`), Deck model, OS/compositor
versions and Steam Input template with each hardware test result. Any failure
should include the section, control sequence, expected/observed result and
whether restarting the shell restores operation.

Required device checks include the entire startup/profile/navigation flow using
built-in controls, real game and app launches, return from games, actual tiled
desktop/window/workspace actions, media playback, sound/brightness/battery,
controller reconnect, suspend/resume and performance. Those checks remain open
until performed on the physical handheld.
