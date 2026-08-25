# Architecture

RuneScape Two follows one rule: **one responsibility has one canonical owner**.

## Layers

| Layer | Owns | Must not own |
| --- | --- | --- |
| `core/` | reusable mechanics: mouse, keyboard, targeting, screenshots, matching | game-specific workflows or tester UI |
| `core/vision/` | image/colour detection, areas, templates, persisted vision settings | actions, sensors, UI |
| `definitions/` | read-only questions about game state | clicks, movement, tester code |
| `actions/` | game actions built from core + definitions | low-level matching implementations |
| `tools/` | calibration, testing, setup and debugging | canonical production algorithms |
| `config/` | data and user settings | Python logic |
| `tests/` | contracts and regression protection | production behavior |

## Where does new code go?

| I want to change... | Canonical location |
| --- | --- |
| template matching algorithm | `core/vision/template_matching.py` |
| template candidate scoring | `core/vision/template_analysis.py` |
| production image hits | `core/vision/image_detection.py` |
| template files/settings/cache | `core/vision/templates.py` |
| colour detection | `core/vision/colour_detection.py` |
| colour/blob analysis | `core/vision/colour_analysis.py` |
| colour preset storage | `core/vision/colour_presets.py` + `colour_preset_meta.py` |
| areas/screenshots/offsets | `core/vision/areas.py`, `screenshots.py`, `offsets.py` |
| mouse execution | `core/mouse.py` |
| image/colour/area mouse actions | `core/mouse_actions.py` |
| external mouse provider | `core/mouse_engine.py` |
| provider-plan validation | `core/mouse_plan.py` |
| mouse runtime state/locks/stop | `core/mouse_runtime.py` |
| a state question such as `is_bank_open` | `definitions/<domain>/` |
| definition discovery metadata | `definitions/registry.py` |
| an action such as `open_bank` | `actions/<domain>/` |
| Vision Tester UI | `tools/vision_tester/` |

## Vision flow

```text
capture_area
    -> core vision analysis
    -> production result
    -> definition/action/tool consumer
```

Template matching has exactly one scoring path:

```text
template_matching.py
    -> template_analysis.py
    -> image_detection.py / tester UI
```

Colour analysis has exactly one implementation path:

```text
colour_detection.py + colour_analysis.py
    -> production definitions/actions / tester UI
```

## Dependency direction

Prefer dependencies to point downward:

```text
tools/actions/definitions
          -> core
```

`core` must never depend on `tools`, `actions` or `definitions`.

## Minimalism rules

1. Do not create a second implementation for an existing responsibility.
2. Extend the canonical owner instead of copying its algorithm into a tester.
3. Prefer a plain function or small class over a framework or plugin layer.
4. A compatibility adapter may re-export old names, but it must contain no implementation.
5. Delete adapters once no supported caller needs them.
6. Do not add a dependency when the standard library or an existing dependency is enough.
7. Every refactor must keep the public behavior covered by tests or a GUI smoke test.

## Tester rule

A tester may visualize or control production logic, but must not reimplement it. If a tester needs a calculation, that calculation belongs in `core` first.
