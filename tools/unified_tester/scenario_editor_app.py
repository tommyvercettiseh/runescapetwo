from __future__ import annotations

from tools.unified_tester.inventory_app import UnifiedTester as InventoryTester
from tools.unified_tester.yaml_scenario_editor import YamlScenarioEditor


class UnifiedTester(InventoryTester):
    """Unified tester with a declarative YAML scenario tab."""

    def __init__(self) -> None:
        super().__init__()
        self.geometry("1000x760")
        self.minsize(900, 680)

        self.scenario_editor = YamlScenarioEditor(
            self.tabs,
            bot_id_var=self.bot_id_var,
            status_callback=self.status_var.set,
        )
        self.tabs.insert(2, self.scenario_editor, text="Scenario")


if __name__ == "__main__":
    UnifiedTester().mainloop()
