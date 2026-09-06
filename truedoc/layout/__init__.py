"""Layout detection: page image -> labelled regions.

Detectors are pluggable. Every detector returns `Region` objects in PDF point
coordinates so downstream code never needs to know the image resolution.
"""

from truedoc.layout.base import LayoutDetector, Region, RegionKind  # noqa: F401
