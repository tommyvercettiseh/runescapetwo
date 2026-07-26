# Changelog

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
