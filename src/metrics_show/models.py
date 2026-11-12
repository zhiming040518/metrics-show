"""Wire models for the versioned metrics API."""

import math
import time
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Metric(Payload):
    name: str = Field(min_length=1, max_length=120)
    display: Literal["value", "line", "both"] = "line"
    x: str = Field(default="step", max_length=120)
    label: str = Field(default="", max_length=120)
    unit: str = Field(default="", max_length=30)


class Event(Payload):
    id: UUID = Field(default_factory=uuid4)
    step: float
    timestamp: float = Field(default_factory=time.time)
    values: dict[str, float] = Field(min_length=1, max_length=200)

    @field_validator("values")
    @classmethod
    def validate_values(cls, values):
        if any(not name or len(name) > 120 for name in values):
            raise ValueError("Metric names must have 1 to 120 characters")
        if any(not math.isfinite(value) for value in values.values()):
            raise ValueError("Metric values must be finite")
        return values


class Batch(Payload):
    events: list[Event] = Field(min_length=1, max_length=200)
