from __future__ import annotations

from . import enhanced_ui


_original_build = enhanced_ui.preset_ui.PresetColourPage._build


def _build_without_binary_mask(self) -> None:
    _original_build(self)

    # Keep the detector pipeline intact, but remove the redundant visual mask.
    # Live area and Isolated colour are the two useful operator views.
    try:
        previews = self.capture_view.master.master
        mask_frame = self.mask_view.master
        isolated_frame = self.isolated_view.master

        mask_frame.grid_remove()
        isolated_frame.grid_configure(column=1, padx=(4, 0))
        previews.columnconfigure(0, weight=1, uniform="preview")
        previews.columnconfigure(1, weight=1, uniform="preview")
        previews.columnconfigure(2, weight=0, uniform="")
    except Exception:
        # A layout failure should never stop the tester from launching.
        pass


def install_colour_view_cleanup() -> None:
    if enhanced_ui.preset_ui.PresetColourPage._build is not _build_without_binary_mask:
        enhanced_ui.preset_ui.PresetColourPage._build = _build_without_binary_mask


__all__ = ["install_colour_view_cleanup"]
