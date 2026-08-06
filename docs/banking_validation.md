# Banking live validation

Deze checklist is de handmatige eindcontrole voor de banking-laag. De code stopt bewust veilig wanneer een voorwaarde niet aantoonbaar klopt.

## Vooraf

- `Bank_Deposit` wordt betrouwbaar gevonden wanneer de bank open is.
- `ScreenCross` wordt betrouwbaar gevonden bij een open interface.
- `Inventory_Area` en `Inventory_Slot_1` tot en met `Inventory_Slot_28` liggen exact goed.
- Iedere protected image, bijvoorbeeld `Item_Axe`, heeft een actuele template.
- De bank quantity staat handmatig op `All`.
- De juiste RuneLite-client heeft focus voordat een keyboardaction zoals `find_bank()` start.

## Testvolgorde in Start Unified Tester.bat

1. Sensors / Bank / Is bank visible.
2. Sensors / Bank / Is bank open.
3. Sensors / Inventory / Is inventory empty en Is inventory full.
4. Actions / Bank inventory met Dry run aan.
5. Controleer `excluded_slots`, `remaining_slots` en `selected_slot`.
6. Test een ontbrekende protected image. Verwacht FALSE en nul clicks.
7. Test met één bankbaar item en Dry run uit.
8. Test meerdere gelijke items met bank quantity `All`.
9. Test één protected item plus meerdere bankbare items.
10. Test Close bank en daarna Open bank afzonderlijk.

## Verwachte fail-safe resultaten

- Bank niet open: action stopt vóór een inventoryclick.
- Protected image niet gevonden: action stopt vóór een verdere click.
- Inventory verandert niet na een click: action stopt en noemt quantity `All`, focus of slotdetectie.
- Bank sluit tijdens de action: action stopt direct.
- Maximum aantal clicks bereikt: action stopt zonder oneindige loop.
- Emergency stop: actieve mouseaction wordt afgebroken; bij drop inventory wordt Shift via `finally` losgelaten.

## Nog fysiek te bevestigen

- HSV-grenzen en `EMPTY_THRESHOLD` van de inventoryscanner.
- Templatekwaliteit bij verschillende helderheid, scaling en RuneLite-layouts.
- Exacte reactietijd tussen bankclick en inventory-update.
- Clientfocus bij meerdere RuneLite-vensters.
- Een toekomstige sensor voor bank quantity `All`; hiervoor moet eerst een betrouwbare template of vaste area worden vastgelegd.
