from django.contrib.gis.db.models import PointField
from django.test import SimpleTestCase

from stations.models import RawStationImport, Station


class StationSchemaTests(SimpleTestCase):
    def test_raw_station_import_preserves_staging_shape(self) -> None:
        fields = RawStationImport._meta

        self.assertFalse(fields.get_field("opis_id").unique)
        self.assertEqual(fields.get_field("opis_id").max_length, 20)
        self.assertEqual(fields.get_field("retail_price").max_digits, 6)
        self.assertEqual(fields.get_field("retail_price").decimal_places, 3)
        self.assertIsNotNone(fields.get_field("imported_at"))

    def test_station_schema_matches_deduped_location_table(self) -> None:
        fields = Station._meta
        location_field = fields.get_field("location")

        self.assertTrue(fields.get_field("opis_id").unique)
        self.assertEqual(fields.get_field("retail_price").max_digits, 6)
        self.assertEqual(fields.get_field("retail_price").decimal_places, 3)
        self.assertIsInstance(location_field, PointField)
        self.assertTrue(location_field.null)
        self.assertEqual(location_field.srid, 4326)
        self.assertTrue(any(index.name for index in fields.indexes))
