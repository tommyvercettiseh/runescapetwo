# RuneScape Two

Eenvoudige en uitbreidbare basis voor mouse, keyboard en vision.

## Hoofdregel

Elke `.py` heeft één duidelijk doel. Scripts beschrijven wat er gebeurt. De core bepaalt hoe het gebeurt.

## Bot-id en areas

Alle areas worden één keer gemeten op bot 1. De geselecteerde `bot_id` voegt daarna precies één desktop-offset toe.

```text
lokale area van bot 1
        +
offset van bot_id
        =
absolute screenshotregio
```

```python
from core import vision

bot_id = 2

local_inventory = vision.get_area("Inventory_Area")
absolute_inventory = vision.get_region("Inventory_Area", bot_id=bot_id)
image, region = vision.capture_area("Inventory_Area", bot_id=bot_id)
```

De standaard offsets staan in `config/bot_offsets.json`:

```json
{
  "1": [0, 0],
  "2": [958, 0],
  "3": [0, 498],
  "4": [958, 498]
}
```

`BOT_ID` kan door een runner als environment variable worden gezet. Een expliciete `bot_id=` bij een functie heeft voorrang.

## Simpel gebruik

```python
from core import keyboard, mouse, vision

bot_id = 2

hit = vision.find_image("bank", area="game", bot_id=bot_id)
if hit:
    mouse.move_to(*hit.center)
    mouse.click()

visible = vision.image_exists(
    "inventory_full",
    area="Inventory_Area",
    bot_id=bot_id,
)

keyboard.press("space")
```

Image detection, colour detection en de testtools gebruiken dezelfde area- en offsetroute:

```text
get_area
→ apply_offset
→ capture_area
→ detectie
→ absoluut resultaat
```

Er is geen publieke `offset=(x, y)` parameter meer in de vision-API.

## Structuur

```text
runescapetwo/
├── app.py
├── assets/
│   └── images/
├── config/
│   ├── areas.json
│   ├── bot_offsets.json
│   ├── colour_presets.json
│   ├── sensor_checks.json
│   └── templates_meta.json
├── core/
│   ├── mouse.py
│   ├── keyboard.py
│   ├── profile.py
│   ├── movements/
│   └── vision/
│       ├── api.py
│       ├── areas.py
│       ├── offsets.py
│       ├── screenshots.py
│       ├── image_detection.py
│       ├── colour_detection.py
│       ├── colour_presets.py
│       ├── template_matching.py
│       ├── color_matching.py
│       ├── templates.py
│       └── models.py
├── tools/
│   ├── vision_tester/
│   ├── image_tester/
│   └── colour_tester/
└── tests/
```

## Image vision

Plaats PNG-bestanden in `assets/images/`.

```python
from core import vision

bot_id = 3

hit = vision.find_image("bank", area="game", bot_id=bot_id)
hits = vision.find_all_images("tree", area="game", bot_id=bot_id)
visible = vision.image_exists("inventory_full", area="Inventory_Area", bot_id=bot_id)
hit = vision.wait_for_image("bank_open", area="game", bot_id=bot_id)
vision.click_image("bank_button", area="game", bot_id=bot_id, wait=True)
vision.wait_until_gone("loading", area="game", bot_id=bot_id)
```

Iedere template gebruikt in productie precies één opgeslagen OpenCV-methode. Templates, metadata en de LAB-kleurweergave worden gecachet.

## Live Image Tester

```bash
python -m tools.image_tester.app
```

De tester vergelijkt de OpenCV-methodes live, toont geldige en afgewezen matches en slaat de gekozen productiemethode op in `config/templates_meta.json`.

## Colour vision

`config/colour_presets.json` begint leeg. Maak kleuren aan met het pipet in de live tester. Een preset bevat alleen de HSV-ranges van de kleur; area, bot en gebruiksregel staan in de functieaanroep.

Dezelfde kleur kan daardoor verschillende doelen hebben.

Een klein aantal rode pixels in de HP-area:

```python
if vision.colour_exists(
    "red",
    area="HP_Area",
    bot_id=bot_id,
    minimum_pixels=8,
):
    print("Low HP")
```

Een groot rood gemarkeerd target in het speelveld:

```python
blobs = vision.find_colour_blobs(
    "red",
    area="game",
    bot_id=bot_id,
    minimum_area_px=500,
)
```

`minimum_pixels` kijkt naar het totale aantal kleurpixels in de area. `minimum_area_px` kijkt naar het exacte aantal verbonden kleurpixels per blob.

Een gevonden blob bevat absolute coördinaten, een centroid en een veilig punt diep binnen de gekleurde vorm:

```python
blob = vision.find_colour(
    "purple",
    area="game",
    bot_id=bot_id,
    minimum_area_px=200,
)

if blob:
    mouse.move_to(*blob.random_point(padding=3))
```

## Live Colour Tester

```bash
python -m tools.colour_tester.app
```

Werkwijze:

1. Kies bot en area.
2. Typ een presetnaam, bijvoorbeeld `purple` of `red`.
3. Activeer het pipet en klik op de opvallende kleur.
4. Pas de HSV-tolerantie en minimum- of maximumblobgrootte live aan.
5. Controleer het masker en de groene kaders met exacte pixelwaarde.
6. Sla de kleurpreset op.

De tester en productie gebruiken dezelfde mask-, pixeltelling- en blobfuncties. Rood dat rond het einde van de HSV-schaal ligt wordt automatisch als twee ranges opgeslagen.

## Unified Vision Tester

```bash
python -m tools.vision_tester.app
```

De Unified Vision Tester heeft drie subpagina's:

- **Colour testing** voor areas, pipetpresets, maskers en exacte blobpixels.
- **Image testing** voor meerdere geselecteerde templates op één screenshot per frame.
- **Sensor checker** voor live regels zoals `low_hp`, `in_combat` en `blue_target_found`.

Typ een deel van een area-, preset-, template- of sensornaam om de lijst direct te filteren. De liveknop blijft zichtbaar aan of uit staan. In de kleurtester blijft het pipet actief voor meerdere kleurmetingen totdat je het zelf uitschakelt. Dominante kleuren worden als kleurvlakken met RGB-, HSV- en percentagewaarden getoond.

De Sensor checker ondersteunt drie soorten checks:

```text
colour_exists  → totaal aantal kleurpixels is hoog genoeg
colour_blob    → minimaal één verbonden kleurblob is groot genoeg
image_exists   → een opgeslagen image-template is gevonden
```

Voorbeeldconfiguratie in `config/sensor_checks.json`:

```json
{
  "low_hp": {
    "kind": "colour_exists",
    "value": "red",
    "area": "HP_Area",
    "threshold": 8,
    "enabled": true
  },
  "blue_target_found": {
    "kind": "colour_blob",
    "value": "blue",
    "area": "game",
    "threshold": 500,
    "enabled": true
  },
  "in_combat": {
    "kind": "image_exists",
    "value": "combat_icon.png",
    "area": "game",
    "threshold": 1,
    "enabled": true
  }
}
```

De sensorpagina toont live `TRUE`, `FALSE`, `UIT` of een duidelijke configuratiefout. Iedere sensor gebruikt de normale productie-API, zodat de checker hetzelfde antwoord geeft als het latere script.

## Installeren en controleren

```bash
pip install -r requirements.txt
python app.py
pytest
```

`app.py` voert geen clicks of toetsen uit. Het toont alleen de geladen bot-id, offsets en lokale en absolute regions.
