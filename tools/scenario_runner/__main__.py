from __future__ import annotations

import argparse

from .runner import load_scenario, run_scenario_with_console_trace


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one RuneScape Two YAML scenario.")
    parser.add_argument("scenario", help="Path to a scenario YAML file.")
    parser.add_argument("--bot", type=int, default=None, help="Override bot_id from YAML.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate conditions and preview actions without sending action input.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate YAML, actions, definitions, templates and areas only.",
    )
    args = parser.parse_args()

    if args.validate:
        data = load_scenario(args.scenario)
        print(f"VALID: {data['name']}")
        return 0

    result = run_scenario_with_console_trace(
        args.scenario,
        bot_id=args.bot,
        dry_run=args.dry_run,
    )
    print(
        f"RESULT: {'TRUE' if result.success else 'FALSE'} | "
        f"steps={result.executed_steps} | {result.message}"
    )
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
