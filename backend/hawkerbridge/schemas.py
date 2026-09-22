from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class ResetPassword(StrictModel):
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

    @field_validator("email")
    @classmethod
    def lowercase(cls, value):
        return value.lower()


class Credentials(ResetPassword):
    password: str = Field(min_length=1, max_length=256)


class Registration(Credentials):
    name: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=12, max_length=256)


class AnalysisRequest(StrictModel):
    date: date
    radius_m: int = Field(default=800, ge=200, le=3000)
    senior_weight: float = Field(default=2, ge=1, le=5)
    rescheduled_closure_ids: list[str] = Field(default_factory=list, max_length=600)
    planning_areas: list[str] = Field(default_factory=list, max_length=55)

    @field_validator("date")
    @classmethod
    def supported_date(cls, value):
        if not date(2000, 1, 1) <= value <= date(2100, 12, 31):
            raise ValueError("Choose a date between 2000 and 2100")
        return value


class OptimiseRequest(AnalysisRequest):
    budget: float = Field(default=1500, ge=0, le=100000)
    site_cost: float = Field(default=300, ge=1, le=10000)
    meal_cost: float = Field(default=4, ge=1, le=100)
    meals_per_site: int = Field(default=150, ge=1, le=5000)
    max_sites: int = Field(default=3, ge=0, le=20)
    participation_rate: float = Field(default=0.05, ge=0.001, le=1)

    @field_validator("budget", "site_cost", "meal_cost")
    @classmethod
    def cents_only(cls, value):
        if abs(value * 100 - round(value * 100)) > 1e-6:
            raise ValueError("Use at most two decimal places for costs")
        return value


class PlanCreate(StrictModel):
    title: str = Field(min_length=1, max_length=140)
    parameters: OptimiseRequest
    notes: str = Field(default="", max_length=4000)


class PlanPatch(StrictModel):
    expected_updated_at: str = Field(min_length=10, max_length=64)
    title: str | None = Field(default=None, min_length=1, max_length=140)
    notes: str | None = Field(default=None, max_length=4000)
    status: Literal["draft", "reviewed"] | None = None
