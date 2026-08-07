from .template_plus import install_template_plus
from .area_overlay_toggle import install_area_overlay_toggle
from .colour_view_cleanup import install_colour_view_cleanup

install_template_plus()
install_area_overlay_toggle()
install_colour_view_cleanup()

from . import unified_plus
from .colour_browser import install_colour_browser

install_colour_browser()

from .colour_recording import install_colour_recording

install_colour_recording()

VisionTester = unified_plus.VisionTester
main = unified_plus.main


__all__ = ["VisionTester", "main"]


if __name__ == "__main__":
    main()
