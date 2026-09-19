from decimal import Decimal

import pytest
from django.contrib.gis.geos import LineString, Point

from stations.models import PricingDataset, Station
from trips.models import FuelStop, TripPlan
from trips.reports import TripPdfReportService


@pytest.mark.django_db
def test_generate_trip_pdf_with_stops() -> None:
    dataset = PricingDataset.objects.create(
        version_code="OPIS-PDF-TEST",
        filename="test.csv",
        file_hash="hash_pdf_test",
        station_count=100,
        is_active=True,
    )
    station1 = Station.objects.create(
        opis_id="PDF_STATION_1",
        name="Pilot Travel Center #123",
        city="Marion",
        state="IL",
        retail_price=Decimal("2.929"),
        location=Point(-88.93, 37.73, srid=4326),
    )
    station2 = Station.objects.create(
        opis_id="PDF_STATION_2",
        name="Love's Travel Stop #456",
        city="Texarkana",
        state="TX",
        retail_price=Decimal("2.857"),
        location=Point(-94.04, 33.42, srid=4326),
    )

    trip = TripPlan.objects.create(
        start_input="Chicago, IL",
        end_input="Dallas, TX",
        start_point=Point(-87.6298, 41.8781, srid=4326),
        end_point=Point(-96.7970, 32.7767, srid=4326),
        route_geometry=LineString([(-87.6, 41.8), (-96.8, 32.7)], srid=4326),
        total_distance_miles=Decimal("968.45"),
        total_gallons=Decimal("96.845"),
        total_cost=Decimal("135.09"),
        cache_key="pdf_test_cache_key_with_stops",
        pricing_dataset=dataset,
        ai_explanation=(
            "Optimal stops selected along corridor avoiding high price zones."
        ),
    )

    FuelStop.objects.create(
        trip_plan=trip,
        station=station1,
        stop_order=1,
        distance_from_start_miles=Decimal("303.73"),
        gallons_purchased=Decimal("28.334"),
        price_per_gallon=Decimal("2.929"),
        cost=Decimal("82.99"),
    )
    FuelStop.objects.create(
        trip_plan=trip,
        station=station2,
        stop_order=2,
        distance_from_start_miles=Decimal("783.34"),
        gallons_purchased=Decimal("18.511"),
        price_per_gallon=Decimal("2.857"),
        cost=Decimal("52.89"),
    )

    service = TripPdfReportService()
    pdf_bytes = service.generate_trip_pdf(trip)

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-1.")
    assert len(pdf_bytes) > 2000


@pytest.mark.django_db
def test_generate_trip_pdf_without_stops() -> None:
    trip = TripPlan.objects.create(
        start_input="Chicago, IL",
        end_input="Milwaukee, WI",
        start_point=Point(-87.6298, 41.8781, srid=4326),
        end_point=Point(-87.9065, 43.0389, srid=4326),
        route_geometry=LineString([(-87.6, 41.8), (-87.9, 43.0)], srid=4326),
        total_distance_miles=Decimal("92.10"),
        total_gallons=Decimal("9.210"),
        total_cost=Decimal("0.00"),
        cache_key="pdf_test_cache_key_no_stops",
        ai_explanation=None,
    )

    service = TripPdfReportService()
    pdf_bytes = service.generate_trip_pdf(trip)

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-1.")
    assert len(pdf_bytes) > 2000
