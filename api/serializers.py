import json
from typing import Any

from rest_framework import serializers

from trips.models import FuelStop, TripPlan


class TripPlanRequestSerializer(serializers.Serializer):  # type: ignore[misc]
    start = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        max_length=255,
    )
    end = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        max_length=255,
    )


class FuelStopResponseSerializer(serializers.ModelSerializer):  # type: ignore[misc]
    station_name = serializers.CharField(source="station.name", read_only=True)
    city = serializers.CharField(source="station.city", read_only=True)
    state = serializers.CharField(source="station.state", read_only=True)
    distance_from_start_miles = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        coerce_to_string=False,
    )
    gallons_purchased = serializers.DecimalField(
        max_digits=8,
        decimal_places=3,
        coerce_to_string=False,
    )
    price_per_gallon = serializers.DecimalField(
        max_digits=6,
        decimal_places=3,
        coerce_to_string=False,
    )
    cost = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        coerce_to_string=False,
    )

    class Meta:
        model = FuelStop
        fields = [
            "stop_order",
            "station_name",
            "city",
            "state",
            "distance_from_start_miles",
            "gallons_purchased",
            "price_per_gallon",
            "cost",
        ]


class TripPlanResponseSerializer(serializers.ModelSerializer):  # type: ignore[misc]
    dataset_version = serializers.CharField(
        source="pricing_dataset.version_code", read_only=True, default=None
    )
    route_geometry = serializers.SerializerMethodField()
    fuel_stops = FuelStopResponseSerializer(many=True, read_only=True)
    total_distance_miles = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        coerce_to_string=False,
    )
    total_gallons = serializers.DecimalField(
        max_digits=8,
        decimal_places=3,
        coerce_to_string=False,
    )
    total_cost = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        coerce_to_string=False,
    )

    class Meta:
        model = TripPlan
        fields = [
            "id",
            "start_input",
            "end_input",
            "dataset_version",
            "route_geometry",
            "total_distance_miles",
            "total_gallons",
            "total_cost",
            "fuel_stops",
            "ai_explanation",
            "created_at",
        ]

    def get_route_geometry(self, obj: TripPlan) -> dict[str, Any]:
        if obj.route_geometry is None:
            return {}
        if isinstance(obj.route_geometry, dict):
            return obj.route_geometry
        if isinstance(obj.route_geometry, str):
            try:
                parsed = json.loads(obj.route_geometry)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                return {}
        if hasattr(obj.route_geometry, "geojson"):
            try:
                parsed = json.loads(obj.route_geometry.geojson)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                return {}
        return {}


class TripPlanListSerializer(serializers.ModelSerializer):  # type: ignore[misc]
    dataset_version = serializers.CharField(
        source="pricing_dataset.version_code", read_only=True, default=None
    )
    total_distance_miles = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        coerce_to_string=False,
    )
    total_cost = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        coerce_to_string=False,
    )

    class Meta:
        model = TripPlan
        fields = [
            "id",
            "start_input",
            "end_input",
            "dataset_version",
            "total_distance_miles",
            "total_cost",
            "created_at",
        ]
