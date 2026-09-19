"""Service layer for building LLM prompts and generating trip explanations."""

from typing import Any

from explanations.adapters import FireworksLLMClient, LLMClient
from trips.models import FuelStop, TripPlan

DEFAULT_SYSTEM_PROMPT = (
    "You are a senior freight logistics and dispatch optimization analyst. "
    "Provide clear, professional, plain-language operational rationale explaining "
    "fuel stop selections for commercial truck drivers. Analyze why chosen stations "
    "minimize total trip refuel cost while respecting vehicle range limitations."
)


class ExplanationService:
    """Orchestrates prompt creation from TripPlan data and invokes the LLM client."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm_client = llm_client or FireworksLLMClient()

    def get_system_prompt(self) -> str:
        """Return the persona and constraint instructions for the LLM."""
        return DEFAULT_SYSTEM_PROMPT

    def build_prompt(self, trip_plan: TripPlan) -> str:
        """Construct a structured prompt describing the trip and chosen stops."""
        prefetched: dict[str, Any] = getattr(
            trip_plan, "_prefetched_objects_cache", {}
        )
        if "fuel_stops" in prefetched:
            raw_stops = prefetched["fuel_stops"]
        else:
            raw_stops = list(trip_plan.fuel_stops.all().select_related("station"))

        stops: list[FuelStop] = [
            stop for stop in raw_stops if isinstance(stop, FuelStop)
        ]

        lines: list[str] = [
            f"Trip Route: {trip_plan.start_input} to {trip_plan.end_input}",
            f"Total Distance: {trip_plan.total_distance_miles} miles",
            f"Total Estimated Fuel: {trip_plan.total_gallons} gallons",
            f"Total Refuel Cost: ${trip_plan.total_cost}",
            "",
            "Vehicle Operating Parameters:",
            "- Max range on a full tank: 500 miles (50 gallon tank at 10 MPG).",
            "- The truck departs the starting location with a full tank at zero cost.",
            "",
        ]

        if not stops:
            lines.extend(
                [
                    "Fuel Stops Selected: 0 (No fuel stops required).",
                    "Reason: The total route distance is within the 500-mile vehicle "
                    "range, so the truck reaches the destination without refueling.",
                ]
            )
        else:
            lines.append("Selected Fuel Stops along Route:")
            for stop in stops:
                station = getattr(stop, "station", None)
                station_name = getattr(station, "name", "Fuel Station")
                city = getattr(station, "city", "")
                state = getattr(station, "state", "")
                loc_str = f"{city}, {state}".strip(", ")
                lines.append(
                    f"- Stop {stop.stop_order}: {station_name} in {loc_str} "
                    f"at mile {stop.distance_from_start_miles} "
                    f"({stop.gallons_purchased} gal @ "
                    f"${stop.price_per_gallon}/gal, Cost: ${stop.cost})"
                )

        lines.extend(
            [
                "",
                "Instructions for Explanation:",
                "In 2-4 sentences, clearly and concisely explain to the "
                "driver why these stops were selected. Highlight price "
                "advantages and range management. Do not include markdown "
                "headers, internal reasoning tags, or conversational fluff.",
            ]
        )

        return "\n".join(lines)

    def explain(self, trip_plan: TripPlan) -> str:
        """Generate a concise plain-language rationale for the given trip plan."""
        prompt = self.build_prompt(trip_plan)
        return self._llm_client.generate_explanation(
            prompt,
            system_prompt=self.get_system_prompt(),
        )

    def build_fallback_explanation(self, trip_plan: TripPlan) -> str:
        """Construct a deterministic operational summary when LLM generation fails."""
        prefetched: dict[str, Any] = getattr(
            trip_plan, "_prefetched_objects_cache", {}
        )
        if "fuel_stops" in prefetched:
            raw_stops = prefetched["fuel_stops"]
        else:
            raw_stops = list(trip_plan.fuel_stops.all().select_related("station"))

        stops: list[FuelStop] = [
            stop for stop in raw_stops if isinstance(stop, FuelStop)
        ]

        if not stops:
            return (
                f"The total journey distance of {trip_plan.total_distance_miles} miles "
                f"is within the commercial vehicle's 500-mile operating range on a full "
                f"departure tank. No en-route refueling stops are required to reach the destination."
            )

        cheapest = min(stops, key=lambda s: s.price_per_gallon)
        station = getattr(cheapest, "station", None)
        st_name = getattr(station, "name", "fuel station") if station else "fuel station"
        city = getattr(station, "city", "") if station else ""
        state = getattr(station, "state", "") if station else ""
        loc_str = f"{city}, {state}".strip(", ")
        loc_display = f" in {loc_str}" if loc_str else ""

        return (
            f"Route optimization scheduled {len(stops)} fuel stop(s) over {trip_plan.total_distance_miles} miles "
            f"to respect the vehicle's 500-mile range constraint while minimizing fuel expenditure. "
            f"Stops prioritize low-cost corridor pricing, led by {st_name}{loc_display} "
            f"at ${cheapest.price_per_gallon}/gal, keeping total refuel cost to ${trip_plan.total_cost}."
        )

