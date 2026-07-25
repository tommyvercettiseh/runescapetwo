from __future__ import annotations

import argparse

from .analyzer import analyze_template
from .storage import save_template_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze and save template settings")
    parser.add_argument("image")
    parser.add_argument("--area")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    results = analyze_template(args.image, args.area)
    for row in results:
        print(
            f"{row['method']:<20} "
            f"shape={row['shape_score']:>6.2f} "
            f"color={row['color_score']:>6.2f} "
            f"at=({row['x']}, {row['y']})"
        )

    if args.save and results:
        best = results[0]
        save_template_settings(
            args.image,
            method=best["method"],
            min_shape=max(0.0, best["shape_score"] - 3.0),
            min_color=max(0.0, best["color_score"] - 5.0),
            area=args.area,
        )
        print("Settings saved to config/templates_meta.json")


if __name__ == "__main__":
    main()
