from __future__ import annotations

from core import active_profile_name, load_profile, vision


def main() -> None:
    profile = load_profile("default")
    bot_id = vision.get_bot_id()

    print(f"Active profile: {active_profile_name()}")
    print(f"Mouse method: {profile['mouse']['movement_method']}")
    print(f"Bot id: {bot_id}")
    print(f"Bot offset: {vision.get_bot_offset(bot_id)}")
    print(f"Local game area: {vision.get_area('game')}")
    print(f"Absolute game area: {vision.get_region('game', bot_id=bot_id)}")
    print(f"Absolute inventory area: {vision.get_region('Inventory_Area', bot_id=bot_id)}")
    print("Foundation loaded successfully.")


if __name__ == "__main__":
    main()
