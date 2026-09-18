"""Shared business constants loaded from the process environment."""

import os
from decimal import Decimal

MAX_RANGE_MILES = int(os.environ.get("MAX_RANGE_MILES", "500"))
MPG_CONSTANT = Decimal(os.environ.get("MPG_CONSTANT", "10.0"))
CORRIDOR_BUFFER_MILES = Decimal(os.environ.get("CORRIDOR_BUFFER_MILES", "15"))

# The 48 contiguous US states plus Washington D.C. Excludes AK, HI, PR, territories.
CONTIGUOUS_48_STATES = frozenset(
    {
        "AL", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA",
        "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA",
        "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM",
        "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD",
        "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    }
)
