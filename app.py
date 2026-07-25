from __future__ import annotations

from core import active_profile_name, load_profile, vision


def main() -> None:
    profile = load_profile("default")

    print(f"Active profile: {active_profile_name()}")
    print(f"Mouse method: {profile['mouse']['movement_method']}")
    print(f"Game area: {vision.get_area('game')}")
    print("Foundation loaded successfully.")


if __name__ == "__main__":
    main()
