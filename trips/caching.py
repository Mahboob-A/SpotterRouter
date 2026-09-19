import hashlib
import json
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

import redis
from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry, LineString, Point

from stations.models import PricingDataset, Station
from trips.models import FuelStop, TripPlan
from trips.repositories import TripPlanRepository

logger = logging.getLogger(__name__)


def build_trip_cache_key(
    start_input: str, end_input: str, version_code: str = ""
) -> str:
    """Produce a deterministic 64-character SHA-256 hash from inputs and version."""
    norm_start = " ".join(start_input.strip().lower().split())
    norm_end = " ".join(end_input.strip().lower().split())
    norm_version = version_code.strip()
    combined = (
        f"{norm_start}::{norm_end}::{norm_version}"
        if norm_version
        else f"{norm_start}::{norm_end}"
    )
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def serialize_trip_plan(trip_plan: TripPlan) -> str:
    """Serialize a TripPlan and its prefetched FuelStops to a JSON string."""
    prefetched = getattr(trip_plan, "_prefetched_objects_cache", {})
    if "fuel_stops" in prefetched:
        stops_source = prefetched["fuel_stops"]
    else:
        stops_source = trip_plan.fuel_stops.all()

    fuel_stops_data: list[dict[str, Any]] = []
    for stop in stops_source:
        station = getattr(stop, "station", None)
        fuel_stops_data.append(
            {
                "stop_order": stop.stop_order,
                "station_id": stop.station_id,
                "station_opis_id": getattr(station, "opis_id", ""),
                "station_name": getattr(station, "name", ""),
                "station_city": getattr(station, "city", ""),
                "station_state": getattr(station, "state", ""),
                "distance_from_start_miles": str(stop.distance_from_start_miles),
                "gallons_purchased": str(stop.gallons_purchased),
                "price_per_gallon": str(stop.price_per_gallon),
                "cost": str(stop.cost),
            }
        )

    dataset_version = ""
    pricing_dataset_id = None
    if trip_plan.pricing_dataset_id:
        pricing_dataset_id = str(trip_plan.pricing_dataset_id)
        pricing_ds = getattr(trip_plan, "pricing_dataset", None)
        if pricing_ds is not None:
            dataset_version = str(getattr(pricing_ds, "version_code", "") or "")

    payload: dict[str, Any] = {
        "id": str(trip_plan.id),
        "start_input": trip_plan.start_input,
        "end_input": trip_plan.end_input,
        "start_point": [trip_plan.start_point.x, trip_plan.start_point.y],
        "end_point": [trip_plan.end_point.x, trip_plan.end_point.y],
        "route_geometry": json.loads(trip_plan.route_geometry.geojson),
        "total_distance_miles": str(trip_plan.total_distance_miles),
        "total_gallons": str(trip_plan.total_gallons),
        "total_cost": str(trip_plan.total_cost),
        "cache_key": trip_plan.cache_key,
        "pricing_dataset_id": pricing_dataset_id,
        "dataset_version": dataset_version,
        "ai_explanation": trip_plan.ai_explanation,
        "created_at": (
            trip_plan.created_at.isoformat() if trip_plan.created_at else None
        ),
        "fuel_stops": fuel_stops_data,
    }
    return json.dumps(payload)


def deserialize_trip_plan(payload_str: str) -> TripPlan:
    """Reconstruct a TripPlan with in-memory prefetched FuelStops from JSON."""
    data = json.loads(payload_str)
    route_geom = GEOSGeometry(json.dumps(data["route_geometry"]))
    if not isinstance(route_geom, LineString):
        route_geom = LineString(data["route_geometry"]["coordinates"], srid=4326)
    else:
        route_geom.srid = 4326

    pricing_dataset = None
    ds_id_raw = data.get("pricing_dataset_id")
    ds_id = uuid.UUID(ds_id_raw) if ds_id_raw else None
    if ds_id:
        pricing_dataset = PricingDataset(
            id=ds_id,
            version_code=data.get("dataset_version", ""),
        )

    plan = TripPlan(
        id=uuid.UUID(data["id"]),
        start_input=data["start_input"],
        end_input=data["end_input"],
        start_point=Point(
            float(data["start_point"][0]),
            float(data["start_point"][1]),
            srid=4326,
        ),
        end_point=Point(
            float(data["end_point"][0]),
            float(data["end_point"][1]),
            srid=4326,
        ),
        route_geometry=route_geom,
        total_distance_miles=Decimal(str(data["total_distance_miles"])),
        total_gallons=Decimal(str(data["total_gallons"])),
        total_cost=Decimal(str(data["total_cost"])),
        cache_key=data["cache_key"],
        pricing_dataset_id=ds_id,
        ai_explanation=data.get("ai_explanation"),
        created_at=(
            datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else datetime.now()
        ),
    )
    if pricing_dataset:
        plan.pricing_dataset = pricing_dataset

    fuel_stops: list[FuelStop] = []
    for stop_data in data.get("fuel_stops", []):
        station = Station(
            id=stop_data["station_id"],
            opis_id=stop_data.get("station_opis_id", ""),
            name=stop_data.get("station_name", ""),
            city=stop_data.get("station_city", ""),
            state=stop_data.get("station_state", ""),
            retail_price=Decimal(str(stop_data.get("price_per_gallon", "0.00"))),
        )
        stop = FuelStop(
            trip_plan=plan,
            station=station,
            stop_order=int(stop_data["stop_order"]),
            distance_from_start_miles=Decimal(
                str(stop_data["distance_from_start_miles"])
            ),
            gallons_purchased=Decimal(str(stop_data["gallons_purchased"])),
            price_per_gallon=Decimal(str(stop_data["price_per_gallon"])),
            cost=Decimal(str(stop_data["cost"])),
        )
        fuel_stops.append(stop)

    plan._prefetched_objects_cache = {  # type: ignore[attr-defined]
        "fuel_stops": fuel_stops,
    }
    return plan


class TripCacheManager:
    """Cache-aside manager for trip plans. Checks Redis first, then PostgreSQL."""

    def __init__(
        self,
        redis_client: redis.Redis | None = None,
        repository: TripPlanRepository | None = None,
        ttl_seconds: int = 86400,
    ) -> None:
        self._redis = redis_client
        self._repository = repository or TripPlanRepository()
        self._ttl_seconds = ttl_seconds
        self._redis_prefix = "trip:"

    def _get_redis(self) -> redis.Redis | None:
        if self._redis is not None:
            return self._redis
        redis_url = getattr(settings, "REDIS_URL", "redis://redis:6379/0")
        try:
            return redis.Redis.from_url(redis_url, decode_responses=True)
        except (redis.RedisError, Exception) as exc:
            logger.warning("Failed to initialize Redis client: %s", exc)
            return None

    def get(self, cache_key: str) -> TripPlan | None:
        """Fetch trip plan from Redis fast path, falling back to PostgreSQL."""
        try:
            client = self._get_redis()
            if client is not None:
                cached_data = client.get(f"{self._redis_prefix}{cache_key}")
                if isinstance(cached_data, str):
                    return deserialize_trip_plan(cached_data)
        except (redis.RedisError, Exception) as exc:
            logger.warning("Redis get error for key %s: %s", cache_key, exc)

        persisted = self._repository.get_by_cache_key(cache_key)
        if persisted is not None:
            try:
                self.set(persisted)
            except Exception as exc:
                logger.warning("Failed to repopulate Redis from database: %s", exc)
            return persisted

        return None

    def set(self, trip_plan: TripPlan) -> None:
        """Store serialized trip plan into Redis with configured TTL."""
        try:
            client = self._get_redis()
            if client is not None:
                payload = serialize_trip_plan(trip_plan)
                client.set(
                    f"{self._redis_prefix}{trip_plan.cache_key}",
                    payload,
                    ex=self._ttl_seconds,
                )
        except (redis.RedisError, Exception) as exc:
            logger.warning(
                "Redis set error for key %s: %s",
                trip_plan.cache_key,
                exc,
            )
