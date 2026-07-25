from __future__ import annotations

import argparse

from .analyzer import analyze_template
from .storage import load_template_settings, save_template_settings
from core.vision.template_matching import available_methods


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze and save template settings")
    parser.add_argument("image")
    parser.add_argument("--area")
    parser.add_argument("--bot-id", type=int)
    parser.add_argument("--method", choices=available_methods())
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    results = analyze_template(args.image, args.area, args.bot_id)
    for row in results:
        print(
            f"{row['method']:<20} "
            f"shape={row['shape_score']:>6.2f} "
            f"color={row['color_score']:>6.2f} "
            f"at=({row['x']}, {row['y']})"
        )

    if args.save and results:
        current = load_template_settings(args.image)
        selected_method = args.method or current.method
        selected = next(
            row for row in results if row["method"] == selected_method
        )
        save_template_settings(
            args.image,
            method=selected_method,
            min_shape=max(0.0, selected["shape_score"] - 3.0),
            min_color=max(0.0, selected["color_score"] - 5.0),
            area=args.area if args.area is not None else current.area,
        )
        print("Settings saved to config/templates_meta.json")


if __name__ == "__main__":
    main()
