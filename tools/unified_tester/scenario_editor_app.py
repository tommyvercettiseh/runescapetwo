from __future__ import annotations

from tools.unified_tester.inventory_app import UnifiedTester as InventoryTester
from tools.unified_tester.scenario_builder_dynamic import DynamicScenarioBuilder


class UnifiedTester(InventoryTester):
    """Unified tester with a small drag-and-drop scenario builder."""

    def __init__(self) -> None:
        super().__init__()
        self.geometry("1180x760")
        self.minsize(1000, 680)

        self.scenario_builder = DynamicScenarioBuilder(
            self.tabs,
            bot_id_getter=self._bot_id,
            status_callback=self.status_var.set,
        )
        self.tabs.insert(2, self.scenario_builder, text="Scenario")


if __name__ == "__main__":
    UnifiedTester().mainloop()
