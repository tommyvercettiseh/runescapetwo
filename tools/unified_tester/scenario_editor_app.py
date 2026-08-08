from __future__ import annotations

from tools.unified_tester.inventory_app import UnifiedTester as InventoryTester
from tools.unified_tester.scenario_code_editor import ScenarioCodeEditor


class UnifiedTester(InventoryTester):
    """Unified tester with a self-contained local action editor tab."""

    def __init__(self) -> None:
        super().__init__()
        self.geometry("1000x760")
        self.minsize(900, 680)

        self.scenario_editor = ScenarioCodeEditor(
            self.tabs,
            status_callback=self.status_var.set,
        )
        self.tabs.insert(2, self.scenario_editor, text="Scenario")


if __name__ == "__main__":
    UnifiedTester().mainloop()
