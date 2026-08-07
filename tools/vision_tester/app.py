from .template_plus import install_template_plus
from .area_overlay_toggle import install_area_overlay_toggle
from .colour_view_cleanup import install_colour_view_cleanup

install_template_plus()
install_area_overlay_toggle()
install_colour_view_cleanup()

from .unified_plus import VisionTester, main


__all__ = ["VisionTester", "main"]


if __name__ == "__main__":
    main()
