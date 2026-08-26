# YAML scenarios

Scenarios describe decision flow only. Python remains inside registered Definitions and Actions.

Supported operations:

- `if` with exactly one `definition` or `image_exists` condition
- `action`
- `wait`
- `stop`

Example:

```yaml
name: Gold bars
bot_id: 1

steps:
  - if:
      definition:
        category: Login
        name: Logged in.
    else:
      - action: Login

  - if:
      image_exists:
        image: Item_Gold_Bar
        area: Inventory_Area
    then:
      - stop: success
    else:
      - action: Find bank
      - action: Open bank
```

`Item_Gold_Bar.png` and `Inventory_Area` must already exist. Validation rejects unknown Definitions, Actions, templates and areas before a scenario is run.

Actions can use the existing Unified Tester options through `with`:

```yaml
- action:
    name: Bank inventory
    with:
      protected_images:
        - Item_Gold_Bar
      selection: nearest
```

There is intentionally no arbitrary Python, `eval`, imports or loops in YAML. Reusable behaviour belongs in a Definition or Action and YAML only composes those building blocks.
