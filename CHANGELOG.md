# Changelog

## Unreleased

### Changed
- Redesigned the Unified Vision Tester with a modern dark workspace layout and consistent controls.
- Area, preset, template and sensor selectors now filter immediately on partial, case-insensitive search.
- Live capture is now a persistent, visibly selected on/off toggle on every tester page.
- The colour pipette remains active across repeated samples until explicitly switched off.
- Dominant colours are now displayed as colour swatches alongside their RGB, HSV and percentage values.
- Colour presets now have explicit add, edit and delete actions with a live editable HSV swatch.

## 0.7.1

### Added
- Live debug panel with the five dominant quantized HSV colour groups in the selected area.
- Exact pixel counts and percentages for the selected colour mask.
- An isolated-colour preview that keeps matching pixels in their original colour and turns everything else black.
- Tests for dominant-colour grouping and isolated masks.

## 0.7.0

### Added
- Unified Vision Tester with separate Colour testing, Image testing and Sensor checker tabs.
- Multi-template image testing on one shared area screenshot per frame.
- Configurable live sensor checks for colour presence, colour blobs and image presence.
- `config/sensor_checks.json` as editable storage for named checks such as `low_hp`, `in_combat` and `blue_target_found`.
- Tests for sensor configuration roundtrips and routing to the correct vision API.

### Architecture
- Colour, image and sensor pages remain separate modules and reuse the production vision engines.
- Existing standalone colour and image testers remain available.

## 0.6.1

### Changed
- HSV ranges are now combined with OpenCV bitwise operations instead of a slow NumPy in-place OR over the full mask.
- Connected-component analysis now reuses existing `uint8` masks instead of allocating a second full-size binary copy.

### Performance
- Synthetic 1280×720 colour-mask benchmarks improved from roughly 14–16 ms to roughly 3–4 ms in the development environment.
- Small HP-style areas remain effectively sub-millisecond before screen capture.

## 0.6.0

### Changed
- Colour names now come from editable `config/colour_presets.json` instead of hardcoded Python ranges.
- `colour_exists()` checks total matching pixels, which fits state sensors such as low HP.
- `find_colour_blobs()` keeps blob-size filtering for marked objects such as large targets.
- Blob area now means the exact number of connected mask pixels instead of contour geometry.
- Colour blobs expose a safe interior point based on distance to the blob edge.
- The live Colour Tester uses the same mask and blob engine as production.

### Added
- Pipette sampling with a small robust pixel patch.
- Automatic HSV wrap handling for red.
- Live green blob boxes with exact pixel counts.
- Live minimum and maximum blob filtering.
- Colour preset create, load, save and delete controls.
- Tests proving that one red preset can support both HP presence and large target detection.

### Removed
- Hardcoded colour aliases and built-in HSV ranges.
- Area editing and click-padding settings from colour presets.
- Duplicate mask and blob logic inside the tester.

## 0.5.0

### Changed
- `find_image()` now uses one fixed preset method per template and never runs `ALL` in production.
- Non-normalized OpenCV methods now use z-score plus sigmoid instead of per-frame min/max normalization.
- The strongest shape candidate is no longer the only candidate checked against the colour threshold.
- Candidate selection now uses repeated strongest-hit suppression instead of sorting every pixel above the threshold.
- Template files, metadata, settings and template LAB conversion are cached.
- The live Image Tester uses the exact same matching engine as production.

### Added
- Live previews for every enabled OpenCV method.
- Green boxes for accepted hits and red boxes for shape hits rejected by colour.
- Live processing time and FPS display.
- Preset saving for method, shape threshold, colour threshold and area.
- Tests for ghost-hit prevention, candidate suppression, colour fallback and maximum hit limits.

### Removed
- Duplicate `detection.py` implementation.
- Separate `nms.py` layer.
- Redundant Image Tester analyzer and storage wrappers.
- No `find_first_image()` API was added; image use remains explicit and single-template.

## 0.4.0

### Changed
- `bot_id` is now the normal public way to select one of the four clients.
- Areas remain local bot-1 regions and are translated exactly once to absolute desktop coordinates.
- Image detection, colour detection and the image tester now use the same central `capture_area()` route.
- Vision calls no longer expose a manual `offset=(x, y)` argument.
- Missing template areas fall back to the local `game` area instead of the full desktop.
- Area names support both short names such as `inventory` and RuneScape-style names such as `Inventory_Area`.

### Added
- `get_region(area, bot_id)` for inspecting an area's absolute region.
- Tests for area aliases, four-client offsets, screenshot isolation and prevention of a second click offset.

### Architecture
- `areas.py` owns local area parsing.
- `offsets.py` owns bot-id to desktop-offset conversion.
- `screenshots.py` owns the combined area capture.
- Sensors and scripts can later use `area="Inventory_Area", bot_id=bot_id` without containing offset math.

### Manual verification
- Run the existing Image Tester and Colour Tester on the real four-client layout before merging.

## 0.3.0

### Added
- Centrale `Tester Hub` die zelfstandige testtools als aparte processen start.
- Zelfstandige live `Colour Tester` met botkeuze, area-selectie, HSV-sliders, morphology, blobfilters en klikpuntpreview.
- Zelfstandige grafische `Image Tester` voor vergelijking van alle template-methodes en opslag van de beste instellingen.
- Windows-launchers voor de hub, Colour Tester en Image Tester.
- Projectstatus in de hub voor areas, templates, colour presets en Python-versie.

### Architecture
- Testers behouden hun eigen `.py`-modules en kunnen zonder de hub worden gestart.
- De hub bevat geen detectielogica en is uitsluitend verantwoordelijk voor status en launching.
- Iedere tester draait in een apart proces, zodat een fout in één tool de hub niet afsluit.

### Manual verification
- De grafische Windows-workflow moet lokaal nog worden gecontroleerd met de echte vier-clientopstelling.

## 0.2.0

### Added
- Centrale `bot_id`-naar-offsetconfiguratie voor bot 1 tot en met 4.
- `config/bot_offsets.json` met aanpasbare offsets.
- Losse `image_detection.py` voor template/image-detectie.
- Losse `colour_detection.py` voor HSV-maskers en blobdetectie.
- `ColourBlob`-model met absolute schermcoördinaten.
- Tests voor offsets, kleuraliases, maskers en blobcoördinaten.

### Changed
- `find`, `exists`, `wait`, `wait_until_gone` en `click_image` behouden nu dezelfde botcontext.
- Handmatige `offset=(x, y)` blijft ondersteund voor backwards compatibility.

### Notes
- De bestaande `detection.py` blijft voorlopig aanwezig als interne compatibilitylaag.
