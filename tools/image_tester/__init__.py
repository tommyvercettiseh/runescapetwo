"""Standalone image tester package.

The current tester uses the shared production modules under ``core.vision``.
Keep package import side-effect free so ``python -m tools.image_tester.app``
can start without legacy helper modules.
"""
