from __future__ import annotations

from .area_overlay_toggle import OverlayColourPage


class CompactColourPage(OverlayColourPage):
    """Keep detector state intact while hiding the redundant mask preview."""

    def _build_previews(self) -> None:
        super()._build_previews()

        previews = self.capture_view.master.master
        mask_frame = self.mask_view.master
        isolated_frame = self.isolated_view.master

        mask_frame.grid_remove()
        isolated_frame.grid_configure(column=1, padx=(4, 0))
        previews.columnconfigure(0, weight=1, uniform="preview")
        previews.columnconfigure(1, weight=1, uniform="preview")
        previews.columnconfigure(2, weight=0, uniform="")


__all__ = ["CompactColourPage"]
