"""Shared business constants loaded from the process environment."""

import os
from decimal import Decimal

MAX_RANGE_MILES = int(os.environ.get("MAX_RANGE_MILES", "500"))
MPG_CONSTANT = Decimal(os.environ.get("MPG_CONSTANT", "10.0"))
CORRIDOR_BUFFER_MILES = Decimal(os.environ.get("CORRIDOR_BUFFER_MILES", "15"))
