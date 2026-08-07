from .template_plus import install_template_plus
from .area_overlay_toggle import install_area_overlay_toggle

install_template_plus()
install_area_overlay_toggle()

from .unified_plus import VisionTester, main


__all__ = ["VisionTester", "main"]


if __name__ == "__main__":
    main()
