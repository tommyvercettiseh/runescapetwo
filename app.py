from __future__ import annotations

import time

from core import keyboard, load_profile, mouse


def main() -> None:
    load_profile("default")

    print("Test starts in 3 seconds...")
    time.sleep(3)

    mouse.move_to(800, 500)
    mouse.click()
    keyboard.type_text("Test completed")


if __name__ == "__main__":
    main()
