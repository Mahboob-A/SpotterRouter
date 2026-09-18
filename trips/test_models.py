import uuid
from decimal import Decimal

from django.contrib.gis.geos import LineString, Point
from django.db import IntegrityError
from django.db.models import ProtectedError
import pytest

from stations.models import Station
from trips.models import FuelStop, TripPlan


@pytest.mark.django_db
class TestTripPlanModel:
    def test_create_trip_plan_persists_expected_fields(self) -> None:
        start_pt = Point(-87.6298, 41.8781, srid=4326)
        end_pt = Point(-96.7970, 32.7767, srid=4326)
        route_geom = LineString([start_pt, end_pt], srid=4326)

        trip = TripPlan.objects.create(
            start_input="Chicago, IL",
            end_input="Dallas, TX",
            start_point=start_pt,
            end_point=end_pt,
            route_geometry=route_geom,
            total_distance_miles=Decimal("967.30"),
            total_gallons=Decimal("96.730"),
            total_cost=Decimal("341.52"),
            cache_key="test-cache-key-123",
        )

        assert isinstance(trip.id, uuid.UUID)
        assert trip.start_input == "Chicago, IL"
        assert trip.end_input == "Dallas, TX"
        assert trip.start_point.srid == 4326
        assert trip.end_point.srid == 4326
        assert trip.route_geometry.srid == 4326
        assert trip.total_distance_miles == Decimal("967.30")
        assert trip.total_gallons == Decimal("96.730")
        assert trip.total_cost == Decimal("341.52")
        assert trip.cache_key == "test-cache-key-123"
        assert trip.ai_explanation is None
        assert trip.created_at is not None

    def test_duplicate_cache_key_raises_integrity_error(self) -> None:
        start_pt = Point(-87.6298, 41.8781, srid=4326)
        end_pt = Point(-96.7970, 32.7767, srid=4326)
        route_geom = LineString([start_pt, end_pt], srid=4326)

        TripPlan.objects.create(
            start_input="Chicago, IL",
            end_input="Dallas, TX",
            start_point=start_pt,
            end_point=end_pt,
            route_geometry=route_geom,
            total_distance_miles=Decimal("967.30"),
            total_gallons=Decimal("96.730"),
            total_cost=Decimal("341.52"),
            cache_key="duplicate-key",
        )

        with pytest.raises(IntegrityError):
            TripPlan.objects.create(
                start_input="Chicago, IL",
                end_input="Dallas, TX",
                start_point=start_pt,
                end_point=end_pt,
                route_geometry=route_geom,
                total_distance_miles=Decimal("967.30"),
                total_gallons=Decimal("96.730"),
                total_cost=Decimal("341.52"),
                cache_key="duplicate-key",
            )


@pytest.mark.django_db
class TestFuelStopModel:
    def test_create_fuel_stop_persists_expected_fields(self) -> None:
        start_pt = Point(-87.6298, 41.8781, srid=4326)
        end_pt = Point(-96.7970, 32.7767, srid=4326)
        route_geom = LineString([start_pt, end_pt], srid=4326)

        trip = TripPlan.objects.create(
            start_input="Chicago, IL",
            end_input="Dallas, TX",
            start_point=start_pt,
            end_point=end_pt,
            route_geometry=route_geom,
            total_distance_miles=Decimal("967.30"),
            total_gallons=Decimal("96.730"),
            total_cost=Decimal("341.52"),
            cache_key="trip-for-stop-test",
        )

        station = Station.objects.create(
            opis_id="99001",
            name="Pilot Travel Center",
            city="Effingham",
            state="IL",
            retail_price=Decimal("3.250"),
            location=Point(-88.5434, 39.1200, srid=4326),
        )

        stop = FuelStop.objects.create(
            trip_plan=trip,
            station=station,
            stop_order=1,
            distance_from_start_miles=Decimal("215.40"),
            gallons_purchased=Decimal("21.540"),
            price_per_gallon=Decimal("3.250"),
            cost=Decimal("70.01"),
        )

        assert stop.id is not None
        assert stop.trip_plan == trip
        assert stop.station == station
        assert stop.stop_order == 1
        assert stop.distance_from_start_miles == Decimal("215.40")
        assert stop.gallons_purchased == Decimal("21.540")
        assert stop.price_per_gallon == Decimal("3.250")
        assert stop.cost == Decimal("70.01")
        assert list(trip.fuel_stops.all()) == [stop]

    def test_duplicate_stop_order_per_trip_raises_integrity_error(self) -> None:
        start_pt = Point(-87.6298, 41.8781, srid=4326)
        end_pt = Point(-96.7970, 32.7767, srid=4326)
        route_geom = LineString([start_pt, end_pt], srid=4326)

        trip = TripPlan.objects.create(
            start_input="Chicago, IL",
            end_input="Dallas, TX",
            start_point=start_pt,
            end_point=end_pt,
            route_geometry=route_geom,
            total_distance_miles=Decimal("967.30"),
            total_gallons=Decimal("96.730"),
            total_cost=Decimal("341.52"),
            cache_key="trip-unique-stop-order",
        )

        station1 = Station.objects.create(
            opis_id="99002",
            name="Station 1",
            city="Effingham",
            state="IL",
            retail_price=Decimal("3.250"),
        )
        station2 = Station.objects.create(
            opis_id="99003",
            name="Station 2",
            city="Mount Vernon",
            state="IL",
            retail_price=Decimal("3.150"),
        )

        FuelStop.objects.create(
            trip_plan=trip,
            station=station1,
            stop_order=1,
            distance_from_start_miles=Decimal("200.00"),
            gallons_purchased=Decimal("20.000"),
            price_per_gallon=Decimal("3.250"),
            cost=Decimal("65.00"),
        )

        with pytest.raises(IntegrityError):
            FuelStop.objects.create(
                trip_plan=trip,
                station=station2,
                stop_order=1,
                distance_from_start_miles=Decimal("280.00"),
                gallons_purchased=Decimal("28.000"),
                price_per_gallon=Decimal("3.150"),
                cost=Decimal("88.20"),
            )

    def test_deleting_trip_cascades_to_fuel_stops(self) -> None:
        start_pt = Point(-87.6298, 41.8781, srid=4326)
        end_pt = Point(-96.7970, 32.7767, srid=4326)
        route_geom = LineString([start_pt, end_pt], srid=4326)

        trip = TripPlan.objects.create(
            start_input="Chicago, IL",
            end_input="Dallas, TX",
            start_point=start_pt,
            end_point=end_pt,
            route_geometry=route_geom,
            total_distance_miles=Decimal("967.30"),
            total_gallons=Decimal("96.730"),
            total_cost=Decimal("341.52"),
            cache_key="trip-cascade-test",
        )

        station = Station.objects.create(
            opis_id="99004",
            name="Station Cascade",
            city="Effingham",
            state="IL",
            retail_price=Decimal("3.250"),
        )

        FuelStop.objects.create(
            trip_plan=trip,
            station=station,
            stop_order=1,
            distance_from_start_miles=Decimal("200.00"),
            gallons_purchased=Decimal("20.000"),
            price_per_gallon=Decimal("3.250"),
            cost=Decimal("65.00"),
        )

        assert FuelStop.objects.filter(trip_plan=trip).count() == 1
        trip.delete()
        assert FuelStop.objects.filter(trip_plan_id=trip.id).count() == 0

    def test_deleting_station_referenced_by_fuel_stop_is_protected(self) -> None:
        start_pt = Point(-87.6298, 41.8781, srid=4326)
        end_pt = Point(-96.7970, 32.7767, srid=4326)
        route_geom = LineString([start_pt, end_pt], srid=4326)

        trip = TripPlan.objects.create(
            start_input="Chicago, IL",
            end_input="Dallas, TX",
            start_point=start_pt,
            end_point=end_pt,
            route_geometry=route_geom,
            total_distance_miles=Decimal("967.30"),
            total_gallons=Decimal("96.730"),
            total_cost=Decimal("341.52"),
            cache_key="trip-protect-test",
        )

        station = Station.objects.create(
            opis_id="99005",
            name="Station Protected",
            city="Effingham",
            state="IL",
            retail_price=Decimal("3.250"),
        )

        FuelStop.objects.create(
            trip_plan=trip,
            station=station,
            stop_order=1,
            distance_from_start_miles=Decimal("200.00"),
            gallons_purchased=Decimal("20.000"),
            price_per_gallon=Decimal("3.250"),
            cost=Decimal("65.00"),
        )

        with pytest.raises(ProtectedError):
            station.delete()
