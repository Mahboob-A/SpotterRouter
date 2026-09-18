from dataclasses import dataclass

from django.contrib.gis.geos import Point


@dataclass(frozen=True)
class Coordinates:
    """Immutable coordinate value object."""

    longitude: float
    latitude: float

    def to_point(self) -> Point:
        """Convert coordinates into an SRID 4326 PostGIS Point."""
        return Point(self.longitude, self.latitude, srid=4326)
