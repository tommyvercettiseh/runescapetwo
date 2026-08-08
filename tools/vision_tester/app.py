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

from .colour_delete_undo import install_colour_delete_undo

install_colour_delete_undo()

from .colour_recording import install_colour_recording

install_colour_recording()

from .replay_reset import install_replay_reset

install_replay_reset()

from .hp_stoplight_monitor import install_hp_stoplight_monitor

install_hp_stoplight_monitor()

VisionTester = unified_plus.VisionTester
main = unified_plus.main


__all__ = ["VisionTester", "main"]


if __name__ == "__main__":
    main()
