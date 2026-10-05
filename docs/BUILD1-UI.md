# Build 1 UI integration handoff

The `build1/ui` work started at Core baseline `718816a` and is prepared against Core `0c337c6`, which supports the OmaHome window title. It adds the native visual presentation requested by the user, governed by their three-panel reference render (startup, profile selection, home). No partition, bootloader, Omarchy configuration, workspace backend, controller backend, or launch implementation is changed.

## Logo review status

The visible product name is **OmaHome**. Connected OH Concept 01 is a provisional review draft, shown to the user with a vector source, small-size study and 3D study. It is implemented for startup preview, but must not be treated as the approved final identity until the user responds. The rest of the reference-matched UI is ready for combined QA independently of this logo review.

The repository, Python package, command and config paths retain their existing names. `QApplication.applicationName` retains the existing internal identifier. The visible native window title is **OmaHome**, supported by Core compatibility commit `0c337c6`, which accepts both names while preserving strict PID matching. On-screen branding, dialogs, descriptive CLI text and help copy all use OmaHome.

## Presentation

- One-word **OmaHome** branding throughout the native interface.
- Perspective-projected, extruded OH monogram with pearl surfaces, blue edge light, a horizon backdrop, opening indicator and 360 ms fade into profiles. A/Enter or B/Escape skips startup. Reduced motion disables animation; hidden logo/loading timers stop.
- Cinematic mountain backdrop, translucent dark panels, illustrated avatars, blue focus outlines, vertical navigation, four large home action tiles, and a separate recent/favorites shelf.
- Home, Games, Media, Store, Library, Apps and Settings all use the existing catalog and actions. The initial home shelf says **Explore your Deck** until there are actual recent launches/favorites. Empty Games/Library screens offer real browse/open actions; no fictional installed titles or connected accounts are shown.
- Local Steam cache artwork and desktop icon lookup fall back to offline vector artwork. No image downloads occur while using the app.
- Native graphical detail dialogs retain Core's launch and pin callbacks.

The reference's spaced “OMA STEAM DECK” lettering is intentionally replaced by the user-required one-word branding and 3D OH mark. Background and avatars are original; native controls are not a screenshot of the reference. Avatars are assigned by profile position in this build; there is no avatar customization/storage change.

## Integration boundaries

`omasteamdeck/visuals.py` owns drawing, theme and presentational widgets. `omasteamdeck/assets/mountain-dusk.png` is bundled via `pyproject.toml` package data. The asset is about 2.1 MiB and has no runtime network dependency.

`app.py` changes are limited to imports/base presentation class, the default Home tab, screen composition, empty-state presentation, detail-dialog artwork, controller focus navigation for the vertical sidebar, the splash fade, and focus/scroll restoration. Core's `launch`, `poll`, `eventFilter`, desktop and workspace operations are preserved. `core.py`, `controller.py`, `desktop.py`, `doctor.py`, `run.sh` and the existing tests are unchanged.

Merge with the later Core hardening commits as well. Preserve their QLockFile import/main guard, desktop attach retry, deferred workspace focus, controller sequencing and catalog fixes. UI changes the QtCore import line, so keep both sides' newly added imports when resolving it. Home extends `TABS` to seven entries; section navigation now uses `len(TABS)`. Input smoke tests should account for Home being the first tab.

The integration worker's deferred focused-card scroll fix is included at the end of `show_home`, using `QTimer.singleShot(0, target, callback)` after the new layout settles. The same restoration is used for profile cards. At eight profiles, Add profile is omitted so Exit remains controller reachable.

## Verification

Run from the repository root:

```sh
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v
python tools/capture_visuals.py work/visuals
python -m pip wheel --no-deps --no-build-isolation --wheel-dir work/wheels .
```

41 tests pass on Core `0c337c6`: 32 existing Core/UI tests and 9 added visual/navigation regressions. Added coverage includes sidebar/category navigation, all seven sections and bumper wraparound, real shortcut destinations, search/favorites, eight-profile scrolling/Exit, 130% text/long names at 1280×800, splash skip/fade, reduced motion, hidden animation timers, corrupt desktop icon metadata, and cached Steam art loading. The wheel includes the visual module and background PNG.

`tools/capture_visuals.py` renders startup, transition, profiles, all seven sections, detail dialog and 130% text variants using disposable state. It discovers real installed apps, but intentionally uses an empty game catalog to verify useful empty states. Eight-profile screenshots are disposable QA fixtures, not default accounts.

Physical Steam Deck controls, OLED/LCD color/contrast, touch comfort and on-device frame pacing still require device validation. Desktop offscreen tests do not establish those results. Integration/QA owns combined live launch/workspace/controller testing against the latest Core.

## Artwork provenance

The mountain asset was created with the built-in image-generation tool, copied into `omasteamdeck/assets/mountain-dusk.png`, and is distributed with the UI. The attached user render informed layout, palette and hierarchy; its interface was not flattened into the application. All icons, avatars, service panels, focus frames, horizon and OH geometry are drawn by Qt code.

Final generation prompt:

> Use case: stylized-concept. Asset type: offline background artwork for a native handheld console interface, 1280 by 800, landscape 16:10. Create an original cinematic alpine mountain valley at blue hour: steep rugged dark rocky peaks frame the left and right, distant snowy peak in the center, dusk sky softly glowing muted mauve and dusty violet near the horizon, deep blue charcoal terrain, atmospheric mist and dark pine forest in foreground. Photorealistic premium game launcher wallpaper, very finely detailed realistic mountains, tasteful calm and expensive-looking. Wide composition; sky and skyline in upper third, entire bottom half very dark and low contrast to host readable UI cards. The top center should have a quiet purple dusk glow. No sun disk. No people. This is ONLY the background landscape, with absolutely no UI, cards, borders, logos, text, watermark or typography. Keep dark tones nuanced, not crushed to flat black.
