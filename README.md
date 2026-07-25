# RuneScape Two

Eenvoudige, uitbreidbare basis voor centrale mouse- en keyboard-aansturing.

## Doel

Scripts beschrijven alleen wat er moet gebeuren. De core bepaalt hoe het gebeurt.

```python
from core import mouse, keyboard

mouse.move_to(800, 500)
mouse.click()
keyboard.press("space")
```

## Structuur

```text
core/
  profile.py
  mouse.py
  keyboard.py
  movements/
profiles/
app.py
```

## Profielen

Pas `profiles/default.json` aan om delays, holds, snelheid en movement-methode centraal te wijzigen.

## Starten

```bash
pip install -r requirements.txt
python app.py
```
