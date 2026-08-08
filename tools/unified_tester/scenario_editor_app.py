from __future__ import annotations

from tools.unified_tester.scenario_app import UnifiedTester
from tools.unified_tester.scenario_code_editor import install_scenario_code_editor
from tools.unified_tester.scenario_runner import BANKING_SCENARIO


install_scenario_code_editor(UnifiedTester, BANKING_SCENARIO)


if __name__ == "__main__":
    UnifiedTester().mainloop()
