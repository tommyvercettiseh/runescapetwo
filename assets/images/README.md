# Images

Plaats hier PNG-afbeeldingen die `core.vision` moet herkennen.

Voorbeeld:

```text
assets/images/bank_button.png
```

Gebruik in een script:

```python
from core import vision

hit = vision.find_image("bank_button", area="game")
```
