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

De area-loader accepteert zowel korte namen zoals `inventory` als de bestaande RuneScape-stijl `Inventory_Area`.

De standaard offsets staan in `config/bot_offsets.json`:

```json
{
  "1": [0, 0],
  "2": [958, 0],
  "3": [0, 498],
  "4": [958, 498]
}
```

`BOT_ID` kan door een runner als environment variable worden gezet. Een expliciete `bot_id=` bij een functie heeft voorrang doordat die direct wordt doorgegeven.

## Simpel gebruik

```python
from core import keyboard, mouse, vision

bot_id = 2

hit = vision.find_image(
    "bank",
    area="game",
    bot_id=bot_id,
)

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

Image detection, colour detection en de testtools gebruiken dezelfde route:

```text
get_area
→ apply_offset
→ capture_area
→ detectie
→ absoluut resultaat
```

Er is geen publieke `offset=(x, y)` parameter meer in de vision-API. Daardoor kan een script de offset niet per ongeluk dubbel toepassen.

## Structuur

```text
runescapetwo/
├── app.py
├── assets/
│   └── images/
├── config/
│   ├── areas.json
│   ├── bot_offsets.json
│   └── templates_meta.json
├── core/
│   ├── mouse.py
│   ├── keyboard.py
│   ├── profile.py
│   ├── movements/
│   └── vision/
│       ├── __init__.py
│       ├── api.py
│       ├── areas.py
│       ├── offsets.py
│       ├── screenshots.py
│       ├── image_detection.py
│       ├── colour_detection.py
│       ├── template_matching.py
│       ├── color_matching.py
│       ├── templates.py
│       ├── models.py
│       └── nms.py
├── tools/
├── profiles/
└── tests/
```

## Vision

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

Wanneer geen area wordt meegegeven, gebruikt een template eerst zijn area uit `config/templates_meta.json` en anders `game`. Een zoekopdracht scant daardoor niet stilletjes het volledige bureaublad.

## Image en Colour Testers

```bash
python -m tools.image_tester.app bank --area game
python -m tools.colour_tester.app
```

Beide tools gebruiken dezelfde bot-offsets en areas als de core.

## Installeren en controleren

```bash
pip install -r requirements.txt
python app.py
pytest
```

`app.py` voert geen clicks of toetsen uit. Het toont alleen de geladen bot-id, offsets en lokale en absolute regions.
