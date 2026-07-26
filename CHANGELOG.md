# Changelog

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
