# Tooling line

RuneScape Two keeps only a small set of canonical launchers in the repository root.

## Canonical tools

### Start Unified Vision Tester.bat
Primary vision workspace.

Use it for:
- Colour
- Template
- Sensor/vision checks
- Area Editor

### Start Automation Builder.bat
Primary automation workspace.

Use it for:
- Definitions/Sensors
- Actions
- YAML/card Scenarios
- Production target Inspector
- Live action trace

This is the current `Unified Tester` functionality under a clearer name. Long term, this workspace may be integrated into Unified Vision Tester; until then it remains a separate canonical launcher.

### Start Inventory Checker.bat
Dedicated inventory-grid/debug tool.

### Start Mouse Engine Setup.bat
Dedicated mouse-engine setup/calibration tool.

## Legacy tools

Old standalone tester launchers live in `archive/launchers/` and should not be used for normal development.

Their Python modules remain in `tools/` for now so this cleanup cannot break hidden imports. Remove legacy modules only when their functionality is demonstrably covered by the canonical tools.

## Rule

Do not add another root-level `Start * Tester.bat` for a new feature.

Prefer one of these instead:
1. add the feature to Unified Vision Tester;
2. add automation/runtime functionality to Automation Builder;
3. create a dedicated launcher only when the tool is genuinely a separate calibration/debug workflow like Inventory Checker or Mouse Engine Setup.
