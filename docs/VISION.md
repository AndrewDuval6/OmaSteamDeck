# Product direction

OmaSteamDeck should feel like a console OS, not a Linux desktop.

Build 1 targets **Steam Deck handheld only**. Flow: **app launch → animated 3D OSD logo → profile → console**, with a real Omarchy + Hyprland tiled desktop alongside it. TV/docked optimization comes later. See [BUILD1.md](BUILD1.md) for the current specification.

Design language: a restrained hint of 1990s hacker/workstation culture, modernized with calm typography, negative space, subtle motion and no gratuitous neon/glitch effects.

The long-term Store is a unified consumer layer over sources such as Flatpak/Flathub, selected Arch/Omarchy packages, and managed web apps. Users should see Install / Installed / Update rather than Linux package-manager terminology.

Build 1 runs on an existing Omarchy + Hyprland installation. It excludes disk partitioning, bootloader changes, OS installation and persistent compositor configuration changes.
