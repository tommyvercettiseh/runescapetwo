# RuneScape Two

Eenvoudige en uitbreidbare basis voor mouse, keyboard en image recognition.

## Ontwerpregel

Scripts beschrijven alleen wat er moet gebeuren. De core bepaalt hoe het gebeurt.

```python
from core import keyboard, mouse, vision

hit = vision.find_image("bank_button", area="game")
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
│   └── areas.json
├── core/
│   ├── __init__.py
│   ├── profile.py
│   ├── mouse.py
│   ├── keyboard.py
│   ├── vision.py
│   └── movements/
│       ├── __init__.py
│       └── linear.py
├── profiles/
│   └── default.json
└── requirements.txt
```

## Profielen

Alle timings en gedragsinstellingen staan centraal in `profiles/default.json`.

Daar pas je onder andere aan:

• mouse movement-methode en duur
• click delays en click holds
• keyboard delays en holds
• vision confidence en timeout
• instellingen voor toekomstige movement-methodes

Een ander profiel laden:

```python
from core import load_profile

load_profile("personal")
```

## Vision

Plaats PNG-bestanden in `assets/images/`.

```python
from core import vision

hit = vision.find_image("bank_button", area="game")
hits = vision.find_all_images("tree", area="game")
visible = vision.image_exists("inventory_full", area="inventory")
hit = vision.wait_for_image("bank_open", area="game")
vision.click_image("bank_button", area="game", wait=True)
vision.wait_until_gone("loading", area="game")
```

Gebieden pas je aan in `config/areas.json`.

## Mouse

```python
from core import mouse

mouse.move_to(800, 500)
mouse.click()
mouse.click("right")
mouse.scroll(-3)
```

Nieuwe movement-methodes kunnen worden geregistreerd zonder bestaande scripts te wijzigen.

## Keyboard

```python
from core import keyboard

keyboard.press("space")
keyboard.hold("shift", 0.5)
keyboard.type_text("Hallo")
keyboard.hotkey("ctrl", "a")
```

## Installeren en controleren

```bash
pip install -r requirements.txt
python app.py
```

`app.py` voert geen clicks of toetsen uit. Het controleert alleen of profiel en configuratie correct laden.
