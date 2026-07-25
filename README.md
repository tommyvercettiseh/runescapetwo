# RuneScape Two

Eenvoudige en uitbreidbare basis voor mouse, keyboard en image recognition.

## Hoofdregel

Elke `.py` heeft één duidelijk doel. Scripts beschrijven alleen wat er moet gebeuren. De core bepaalt hoe het gebeurt.

```python
from core import keyboard, mouse, vision

hit = vision.find_image("bank")
if hit:
    mouse.move_to(*hit.center)
    mouse.click()

keyboard.press("space")
```

## Structuur

```text
runescapetwo/
├── app.py
├── assets/
│   └── images/
├── config/
│   ├── areas.json
│   └── templates_meta.json
├── core/
│   ├── mouse.py
│   ├── keyboard.py
│   ├── profile.py
│   ├── movements/
│   └── vision/
│       ├── __init__.py
│       ├── api.py
│       ├── detection.py
│       ├── template_matching.py
│       ├── color_matching.py
│       ├── templates.py
│       ├── screenshots.py
│       ├── areas.py
│       ├── offsets.py
│       ├── models.py
│       └── nms.py
├── tools/
│   └── image_tester/
│       ├── app.py
│       ├── analyzer.py
│       └── storage.py
├── profiles/
│   └── default.json
├── tests/
└── requirements.txt
```

## Vision

Plaats PNG-bestanden in `assets/images/`.

```python
from core import vision

hit = vision.find_image("bank")
hits = vision.find_all_images("tree", area="game")
visible = vision.image_exists("inventory_full", area="inventory")
hit = vision.wait_for_image("bank_open", area="game")
vision.move_to_image("bank", bot_id=2)
vision.click_image("bank_button", area="game", wait=True)
vision.wait_until_gone("loading", area="game")
```

`find_image("bank")` gebruikt automatisch `bank.png` en leest methode, vormdrempel, kleurdrempel en optionele area uit `config/templates_meta.json`.

`move_to_image` en `click_image` kiezen standaard een willekeurig punt binnen
de gevonden afbeelding. De padding vanaf de randen komt uit het actieve profiel
en kan per actie worden overschreven:

```python
vision.move_to_image("bank", bot_id=2)
vision.click_image("bank", bot_id=2, padding=6)
```

De gevonden coördinaten zijn al absolute schermcoördinaten inclusief de
bot-offset. Mouse past daarom geen tweede offset toe.

```json
{
  "_defaults": {
    "method": "TM_CCOEFF_NORMED",
    "min_shape": 85.0,
    "min_color": 60.0
  },
  "bank.png": {
    "method": "TM_CCOEFF_NORMED",
    "min_shape": 90.0,
    "min_color": 72.0,
    "area": "game"
  }
}
```

## Image tester

Analyseer alle zes OpenCV-methodes:

```bash
python -m tools.image_tester.app bank --area game
```

Analyseer en sla de beste methode met veilige marges op:

```bash
python -m tools.image_tester.app bank --area game --save
```

`--save` gebruikt de methode die al voor de template is ingesteld. Kies een
andere methode bewust met `--method`, omdat scores van verschillende OpenCV-
methodes niet altijd rechtstreeks vergelijkbaar zijn:

```bash
python -m tools.image_tester.app bank --area game --method TM_CCORR_NORMED --save
```

De instellingen worden atomisch opgeslagen in `config/templates_meta.json`.

## Profielen

Alle mouse-, keyboard- en algemene visiontimings staan centraal in `profiles/default.json`.

```python
from core import load_profile

load_profile("personal")
```

## Bots en offsets

Selecteer de bot één keer voordat het script begint:

```python
from core import set_bot

set_bot(2)
```

Alle area-gebaseerde visionfuncties gebruiken daarna automatisch de offset uit
`config/bots.json`. Voor bot 2 is dat standaard `(958, 0)`.
Ook `screen` is een normale basisarea in `config/areas.json` en wordt op
dezelfde manier verschoven.

Een proces kan de bot ook via de omgevingsvariabele `BOT_ID` selecteren.
Een expliciete `bot_id` of `offset` op een visionfunctie overschrijft de actieve
bot alleen voor die aanroep.

## Installeren en controleren

```bash
pip install -r requirements.txt
python app.py
pytest
```

`app.py` voert geen clicks of toetsen uit. Het controleert alleen de basisconfiguratie.
