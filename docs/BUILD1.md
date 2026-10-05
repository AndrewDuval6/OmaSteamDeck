# OmaFlow Build 1 specification

Build 1 targets a complete, runnable **Steam Deck handheld experience** combining the controller-first OmaFlow console interface with a real **Omarchy + Hyprland desktop**. The handheld display at **1280 × 800** is the sole product target. TV and docked optimization belong to a later build. The repository and internal package/config identifiers remain OmaSteamDeck / omasteamdeck.

## Target environment and non-negotiable boundaries

- Run as the signed-in user within an **existing Omarchy + Hyprland installation on Steam Deck**, using Python 3.10+, Qt 6 / PySide6 with Qt WebEngine and Qt WebChannel, SDL2 and a working graphical session.
- The console is a native Qt application. Only the startup graphics use an embedded Qt WebEngine view; the menus and backend remain native. No standalone browser window or local HTTP server is required.
- **Do not modify partitions or the bootloader.** No flashing, partition tools, boot entries, OS installer or privileged provisioning are included.
- Do not overwrite Omarchy or Hyprland configuration. Workspace/window integration operates at runtime through Hyprland IPC.
- Stock SteamOS Gaming Mode can run the console when dependencies are available, but it is **not the full Build 1 environment**: it does not supply Omarchy or Hyprland. Running the shell does not install either OS component.
- Existing browser prototype sources remain in `src/` and `index.html` for reference; the supported entry point is `run.sh`.

## Required experience

### Startup and profiles

Launch full screen → animated startup logo rendered using real Three.js/WebGL geometry, materials, lights and camera → profile picker → console. Reduced motion must render a still view of the same Three.js scene. QPainter projected geometry is not an acceptable replacement for the requested startup. Logo design remains subject to review. Profiles can be created and renamed entirely with the controller keyboard. Each profile has its own pinned collection and recent launch requests; preferences and profiles survive restarts. Profiles are not separate Linux accounts or authentication boundaries.

### Console destinations

| Section | Build 1 behavior |
| --- | --- |
| Home | Four controller-accessible category actions plus actual recent launches/favorites, or an honestly labeled exploration shelf for a new profile. |
| Games | Discover installed Steam titles from native / Flatpak Steam and additional Steam libraries; launch through Steam; provide an honest empty state and Open Steam action. |
| Media | Launch YouTube, Spotify, Netflix and Prime Video in the default browser. Accounts, subscriptions and DRM support remain with the service/browser. |
| Store | Open the actual Steam, Flathub, GOG and itch.io storefronts. Buying/installing is delegated to those storefronts; no fake installation state or automatic package changes. |
| Library | Profile-specific pins and recent launch requests across games, apps and media; search and unpin. |
| Apps | Discover visible non-terminal desktop applications, including exported Flatpaks; launch their desktop entry commands without a shell. |
| Settings | Full screen, readable text sizes, reduced motion, profile management, control help, Hyprland workspaces, Omarchy tools, volume, brightness and exit to desktop. |

The UI must have a visible focus ring, readable type, controller-accessible dialogs, scroll-to-focus, touch/click targets, search, useful error messages and empty states. The console remains usable without a network connection; online services require connectivity.

### Real desktop integration

- Dedicated named Hyprland workspaces: **Console**, **Play**, **Media**, **Desktop** (`osd-console`, `osd-play`, `osd-media`, `osd-desktop`). Existing workspaces are preserved.
- Console starts on its own workspace. Games, media and applications request the appropriate workspace before launching. Existing single-instance apps may reuse their current workspace; the window picker can move them explicitly.
- A graphical workspace/window picker lists real compositor windows and offers focus, tile, floating toggle and move-to-workspace actions.
- Tiling is performed by the installed Hyprland layout, including side-by-side native apps. No imitation tiling surface inside the console.
- Hold **View/Back + Start** to focus the console from another app. Hold **View/Back + D-pad** to focus tiles, **+ LB/RB** to change OSD workspaces, **+ X** to tile the focused external app, **+ Y** to move it to Desktop.
- Omarchy integration uses its installed commands for Files, Terminal, system menu, volume and brightness. Missing dependencies produce a clear message.
- Hyprland 0.55+ uses Lua dispatchers; earlier versions use legacy dispatchers. The current host integration test covers 0.56.2; legacy commands have contract tests and require target validation.

### Input and lifecycle

D-pad / left stick navigates, A confirms, B goes back, X pins, Y searches, shoulders change sections, Start opens Settings, and a View/Back tap opens workspaces. Keyboard and touch remain available. SDL supports hotplug, a stick deadzone, directional repeat and edge-triggered action buttons. Normal background gameplay input must not navigate the shell; only explicit desktop chords are handled globally. External applications retain their own input behavior; trackpads/touch are available for apps that are not controller-oriented.

Exiting the shell leaves external applications open. Runtime integration does not write compositor rules, replace desktop bindings, alter screen modes, or modify the OS. App state lives under `$XDG_CONFIG_HOME/omasteamdeck/` (normally `~/.config/omasteamdeck/`).

## Release acceptance

Code completion and physical-device acceptance are distinct. Build 1 cannot be described as Steam Deck hardware-certified until the physical checks below pass.

1. Clean user-local setup and launch on the target Steam Deck Omarchy installation.
2. Full startup flow, all six sections, profiles, launch, pin and search using only the built-in controls.
3. Correct 1280 × 800 rendering, including largest text, touch, keyboard, modal dialogs and long libraries.
4. Real game launch and return; media playback in a compatible browser; installed app launch and failed-launch recovery.
5. Two apps tile correctly; workspace switching, window moving and controller return work on-device.
6. Controller reconnect, Steam Input interaction and no unintended shell action while playing.
7. Volume and brightness operate on Deck hardware; battery reporting is accurate.
8. Sleep/resume retains a usable shell and input. No stuck modifiers or repeated launches.
9. Automated tests and the opt-in compositor smoke test pass.
10. No partition, bootloader, persistent compositor or system package changes occur.

See [TESTING.md](TESTING.md) for actual evidence and outstanding physical checks. Performance, thermals, battery runtime, suspend/resume and DRM playback must be measured on real hardware; desktop tests cannot establish them.
