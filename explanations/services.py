"""Service layer for building LLM prompts and generating trip explanations."""

from typing import Any

from explanations.adapters import FireworksLLMClient, LLMClient
from trips.models import FuelStop, TripPlan

DEFAULT_SYSTEM_PROMPT = (
    "You are a professional logistics fuel-routing analyst. "
    "Provide concise, clear, plain-language explanations of optimal fuel stop "
    "choices for truck drivers."
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
