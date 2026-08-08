from .template_plus import install_template_plus
from .area_overlay_toggle import install_area_overlay_toggle
from .colour_view_cleanup import install_colour_view_cleanup

install_template_plus()
install_area_overlay_toggle()
install_colour_view_cleanup()

from . import unified_plus
from .colour_browser import install_colour_browser

install_colour_browser()

from .manual_colour_save import install_manual_colour_save

install_manual_colour_save()

from .colour_recording import install_colour_recording

install_colour_recording()

from .colour_fire_monitor import install_colour_fire_monitor

install_colour_fire_monitor()

from .replay_reset import install_replay_reset

install_replay_reset()

VisionTester = unified_plus.VisionTester
main = unified_plus.main


__all__ = ["VisionTester", "main"]


if __name__ == "__main__":
    main()
