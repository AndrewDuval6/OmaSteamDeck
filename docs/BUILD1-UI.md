# Build 1 UI integration handoff

The `build1/ui` work started at Core baseline `718816a` and is prepared against Core `ae8f4c1`, which includes the OmaFlow window title and WebEngine runtime preflight. It adds the native visual presentation requested by the user, governed by their three-panel reference render (startup, profile selection, home). No partition, bootloader, Omarchy configuration, workspace backend, controller backend, or launch implementation is changed.

## Logo review status

The user confirmed **OmaFlow** as the final Build 1 name and chose the three-part **Open Flow** direction with a central negative space. Refinement 02 preserves that form, with an asymmetric lifted crown and extended lower return. It is **provisional and awaiting review**; the user has not approved a final logo. Earlier OH/OF monograms, Confluence Loop and Current studies are superseded.

`omasteamdeck/assets/startup/mark.js` is the canonical contour. `python tools/sync_mark.py` generates the matching native SVG. `docs/branding/omaflow-open-flow-review.html` is the review board (serve the repository locally to view its actual Three.js iframe). The icon and 3D scene share the same outline; the model adds a shallow curved surface and beveled depth. Broad face triangles are subdivided before bending so studio reflections remain smooth. This is a design proposal, not a trademark clearance claim.

The user subsequently repeated the brief asking for a different original flow symbol. The separate **Lift** study explores an open rising ribbon with an incoming path joining a broader sweep. It is available in `docs/branding/omaflow-lift-review.html` and the actual Three.js scene with `?preview=1&concept=lift`. The earlier three-part candidate remains the native shell's provisional mark until the user chooses; neither logo is finalized. `python tools/sync_mark.py --concept lift` regenerates the alternate SVG. A `concept` parameter without review mode cannot replace the native mark.

The repository, Python package, command and config paths retain their existing names. `QApplication.applicationName` retains the existing internal identifier. The visible native window title is **OmaFlow**, supported by Core compatibility commit `aef594b`, which accepts the current and legacy names while preserving strict PID matching. On-screen branding, dialogs, descriptive CLI text and help copy all use OmaFlow.

## Presentation

- One-word **OmaFlow** branding throughout the native interface.
- Actual **Three.js 0.186.1 / WebGL2** startup: beveled solid geometry with a curved surface, metallic material, studio environment reflections, four lights, a perspective camera move, staged wordmark and a native profile fade. A/Enter or B/Escape skips startup. Reduced motion draws a static real 3D frame, then enters profiles without a fade. The sidebar icon is static and uses no animation timer.
- Cinematic mountain backdrop, translucent dark panels, illustrated avatars, blue focus outlines, vertical navigation, four large home action tiles, and a separate recent/favorites shelf.
- Home, Games, Media, Store, Library, Apps and Settings all use the existing catalog and actions. The initial home shelf says **Explore your Deck** until there are actual recent launches/favorites. Empty Games/Library screens offer real browse/open actions; no fictional installed titles or connected accounts are shown.
- Local Steam cache artwork and desktop icon lookup fall back to offline vector artwork. No image downloads occur while using the app.
- Native graphical detail dialogs retain Core's launch and pin callbacks.

The reference's spaced “OMA STEAM DECK” lettering is intentionally replaced by the user-required one-word branding and 3D flow mark. Background and avatars are original; native controls are not a screenshot of the reference. Avatars are assigned by profile position in this build; there is no avatar customization/storage change.

## Integration boundaries

`omasteamdeck/visuals.py` owns native drawing, theme and presentational widgets. `startup.py` hosts the offline Three.js page in an isolated, off-the-record Qt WebEngine profile. Its narrow WebChannel only reports ready/complete/error; it exposes no launch, filesystem or system-control API. Local assets are bundled, remote requests are blocked, and the normal Core runtime preflight requires the complete WebEngine installation. No runtime web server is used. `omasteamdeck/assets/mountain-dusk.png` is bundled via `pyproject.toml` package data. The asset is about 2.1 MiB and has no runtime network dependency.

`app.py` changes cover presentation, Home, empty states, details artwork, sidebar focus navigation, startup hosting and profile transitions. Core's launch, SDL polling, keyboard mapping, desktop and workspace operations remain unchanged. The only input-boundary adjustment temporarily scopes the existing Python event filter to the Shell during WebEngine startup, then restores the global filter after browser destruction. This avoids an observed PySide6 6.11 recursion crash in private Qt Quick focus wrappers; controller polling continues throughout. `AA_ShareOpenGLContexts` is set before QApplication creation. Native page margins are restored in `clear()`.

Core runtime/doctor/launcher changes are inherited from `ae8f4c1`, not reimplemented by UI. The startup uses at most 1× pixel ratio, a stable 30 fps cap, 10,508 triangles for Open Flow (6,780 for the Lift study), and two draw calls per scene frame, with no bloom/shadow/postprocessing passes. The small environment map is prepared once. Completion/skip/hide disposes geometry, materials, reflections, animation callbacks and the WebGL context. The animation clock pauses while the page is hidden, resizing preserves the current pose, and disposed scenes cannot restart rendering. An eight-second native watchdog and renderer-error fallback continue to profiles; intentional disposal is not reported as a lost-context error.

Merge with the later Core hardening commits as well. Preserve their QLockFile import/main guard, desktop attach retry, deferred workspace focus, controller sequencing and catalog fixes. UI changes the QtCore import line, so keep both sides' newly added imports when resolving it. Home extends `TABS` to seven entries; section navigation now uses `len(TABS)`. Input smoke tests should account for Home being the first tab.

The integration worker's deferred focused-card scroll fix is included at the end of `show_home`, using `QTimer.singleShot(0, target, callback)` after the new layout settles. The same restoration is used for profile cards. At eight profiles, Add profile is omitted so Exit remains controller reachable.

## Verification

```sh
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v
python tools/capture_visuals.py work/visuals
python -m pip wheel --no-deps --no-build-isolation --wheel-dir work/wheels .
# Complete PySide6 runtime and a working graphical session required:
python tools/check_startup.py
# Separate optional Playwright QA dependency (no app runtime dependency):
PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs CHROMIUM_BIN=/path/to/chromium node tools/check_startup.mjs
```

45 unit tests pass on Core `ae8f4c1`. They cover Core/controller behavior plus sidebar/category navigation, all seven sections, search/favorites, eight-profile scrolling/Exit, 130% text/long names at 1280×800, native splash fallback/skip/fade, reduced motion, local icons and cached Steam art. Offscreen unit tests intentionally use a native wordmark fallback; they do **not** establish WebGL functionality.

Separate real **Wayland Qt WebEngine** smoke tests pass in a complete PySide6 6.11.2 wheel runtime: scene ready with actual WebGL draw calls, automatic profile handoff, disposal, Enter/Escape from the browser focus surface, controller accept/back through the existing poll path before first frame, reduced motion, restored Settings/profile/modal keyboard input, close during loading and a fresh second startup. These controller actions are injected; Integration/QA owns real SDL validation.

Separate Chromium WebGL checks pass for actual geometry and wordmark, timed completion, keyboard/pointer skips, system reduced-motion preference, context loss, unavailable WebGL fallback, no external asset requests and no uncaught page errors. Additional checks cover the alternate study, the 30 fps cap, review-only mark selection and zero frames after disposal. Browser QA uses software WebGL flags only in its test process; production does not set GPU or sandbox flags.

`tools/capture_visuals.py` renders profiles, all sections, details and 130% variants using disposable state. Its `startup-native-only.png` is explicitly a diagnostic fallback, not the 3D experience. The real startup screenshot comes from the WebGL capture. No sample games/accounts are represented as installed or connected.

Physical Steam Deck controls, OLED/LCD contrast, touch comfort and on-device frame pacing still require device validation. Desktop tests do not establish those results. Integration/QA owns combined live launch/workspace/controller testing and the draft integration PR; logo approval remains separate.

## Artwork provenance

The mountain asset was created with the built-in image-generation tool, copied into `omasteamdeck/assets/mountain-dusk.png`, and is distributed with the UI. The attached user render informed layout, palette and hierarchy; its interface was not flattened into the application. Native icons, avatars, service panels and focus frames are drawn by Qt code. The refined logo is code-native vector geometry, rendered statically in Qt and extruded/bent in Three.js. The user-reviewed Open Flow direction came from an image-generation concept study; the current review board is rendered from the implementation itself. The local Three.js distribution retains its MIT license in `assets/startup/vendor/THREE-LICENSE.txt`.

Final generation prompt:

> Use case: stylized-concept. Asset type: offline background artwork for a native handheld console interface, 1280 by 800, landscape 16:10. Create an original cinematic alpine mountain valley at blue hour: steep rugged dark rocky peaks frame the left and right, distant snowy peak in the center, dusk sky softly glowing muted mauve and dusty violet near the horizon, deep blue charcoal terrain, atmospheric mist and dark pine forest in foreground. Photorealistic premium game launcher wallpaper, very finely detailed realistic mountains, tasteful calm and expensive-looking. Wide composition; sky and skyline in upper third, entire bottom half very dark and low contrast to host readable UI cards. The top center should have a quiet purple dusk glow. No sun disk. No people. This is ONLY the background landscape, with absolutely no UI, cards, borders, logos, text, watermark or typography. Keep dark tones nuanced, not crushed to flat black.
