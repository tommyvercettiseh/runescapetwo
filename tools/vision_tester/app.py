from .template_plus import install_template_plus

install_template_plus()

from .unified_plus import VisionTester, main


__all__ = ["VisionTester", "main"]


if __name__ == "__main__":
    main()
