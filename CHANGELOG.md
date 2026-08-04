# Changelog

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
