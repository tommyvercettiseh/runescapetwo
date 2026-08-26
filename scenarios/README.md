# YAML scenarios

Scenarios describe decision flow only. Python remains inside registered Definitions and Actions.

## Normal workflow

Use the **Scenario > Builder** tab in the Unified Tester. The visual cards are the normal editing interface; YAML is the portable storage format underneath.

The Builder supports four card types:

- **IF**: registered Sensor/Definition or generic `image_exists`
- **ACTION**: one registered Action
- **WAIT**: wait a number of seconds
- **STOP**: finish as success or failure

IF cards contain **THEN / TRUE** and **ELSE / FALSE** branches. Both branches can contain the same four card types, including nested IF cards. Cards on the same level execute from top to bottom, so cards after an IF naturally mean "then continue / finally".

Cards can be moved up/down or deleted. Switching to **YAML / Advanced** generates the YAML from the cards. Manual YAML remains available for advanced editing and can be loaded back into the Builder.

## YAML model

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

Actions can use the existing Unified Tester options through `with` in the Advanced YAML view:

```yaml
- action:
    name: Bank inventory
    with:
      protected_images:
        - Item_Gold_Bar
      selection: nearest
```

There is intentionally no arbitrary Python, `eval`, imports or YAML loops. Reusable behaviour belongs in a Definition or Action and YAML only composes those building blocks.
