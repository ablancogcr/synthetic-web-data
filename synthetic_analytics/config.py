from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator, model_validator


COMMERCIAL_INTENTS = {"low", "medium", "high", "very_high"}


class WeightedMultiplier(BaseModel):
    name: str
    multiplier: float = Field(gt=0)
    weight: float = Field(gt=0)


class CountryConfig(WeightedMultiplier):
    region: str = "Unknown"


class SiteConfig(BaseModel):
    name: str
    domain: str
    description: str


class PageConfig(BaseModel):
    page_path: str
    page_type: str
    content_category: str
    phone_brand: str = "none"
    phone_model: str = "none"
    commercial_intent: str
    traffic_weight: float = Field(gt=0)
    engagement_multiplier: float = Field(default=1.0, gt=0)
    account_signup_multiplier: float = Field(default=1.0, gt=0)
    newsletter_signup_multiplier: float = Field(default=1.0, gt=0)

    @field_validator("page_path")
    @classmethod
    def validate_page_path(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("page_path must start with '/'")
        return value

    @field_validator("commercial_intent")
    @classmethod
    def validate_commercial_intent(cls, value: str) -> str:
        if value not in COMMERCIAL_INTENTS:
            raise ValueError(
                "commercial_intent must be one of: low, medium, high, very_high"
            )
        return value


class TrafficChannelConfig(BaseModel):
    source: str
    medium: str
    campaign: str = "none"
    multiplier: float = Field(gt=0)
    weight: float = Field(gt=0)
    account_signup_multiplier: float = Field(default=1.0, gt=0)
    newsletter_signup_multiplier: float = Field(default=1.0, gt=0)


class RandomnessConfig(BaseModel):
    noise_stddev: float = Field(default=0.045, ge=0, le=1)
    min_multiplier: float = Field(default=0.88, gt=0)
    max_multiplier: float = Field(default=1.12, gt=0)
    daily_noise_stddev: float = Field(default=0.025, ge=0, le=1)
    daily_min_multiplier: float = Field(default=0.95, gt=0)
    daily_max_multiplier: float = Field(default=1.05, gt=0)

    @model_validator(mode="after")
    def validate_range(self) -> "RandomnessConfig":
        if self.min_multiplier > self.max_multiplier:
            raise ValueError("randomness.min_multiplier must be <= randomness.max_multiplier")
        if self.daily_min_multiplier > self.daily_max_multiplier:
            raise ValueError(
                "randomness.daily_min_multiplier must be <= daily_max_multiplier"
            )
        return self


class GrowthTrendConfig(BaseModel):
    monthly_growth_rate: float = Field(default=0.02, ge=-0.95, le=1)


class SpecialEventConfig(BaseModel):
    name: str
    start_date: date
    end_date: date
    multiplier: float = Field(gt=0)
    account_signup_multiplier: float = Field(default=1.0, gt=0)
    newsletter_signup_multiplier: float = Field(default=1.0, gt=0)
    page_types: list[str] | None = None
    content_categories: list[str] | None = None
    phone_brands: list[str] | None = None
    countries: list[str] | None = None
    channels: list[str] | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "SpecialEventConfig":
        if self.start_date > self.end_date:
            raise ValueError(f"event {self.name} start_date must be on or before end_date")
        return self


class MetricRulesConfig(BaseModel):
    users_per_session_min: float = Field(default=0.62, gt=0, le=1)
    users_per_session_max: float = Field(default=0.88, gt=0, le=1)
    new_user_rate_min: float = Field(default=0.35, ge=0, le=1)
    new_user_rate_max: float = Field(default=0.68, ge=0, le=1)
    pageviews_per_session_min: float = Field(default=1.4, ge=1)
    pageviews_per_session_max: float = Field(default=3.8, ge=1)
    engagement_rate_min: float = Field(default=0.48, ge=0, le=1)
    engagement_rate_max: float = Field(default=0.76, ge=0, le=1)
    avg_session_duration_seconds_min: int = Field(default=45, gt=0)
    avg_session_duration_seconds_max: int = Field(default=210, gt=0)

    @model_validator(mode="after")
    def validate_bounds(self) -> "MetricRulesConfig":
        pairs = [
            ("users_per_session", self.users_per_session_min, self.users_per_session_max),
            ("new_user_rate", self.new_user_rate_min, self.new_user_rate_max),
            ("pageviews_per_session", self.pageviews_per_session_min, self.pageviews_per_session_max),
            ("engagement_rate", self.engagement_rate_min, self.engagement_rate_max),
            (
                "avg_session_duration_seconds",
                self.avg_session_duration_seconds_min,
                self.avg_session_duration_seconds_max,
            ),
        ]
        for name, lower, upper in pairs:
            if lower > upper:
                raise ValueError(f"metric_rules.{name}_min must be <= {name}_max")
        return self


class ConversionRateConfig(BaseModel):
    base: float = Field(gt=0, le=1)
    min: float = Field(ge=0, le=1)
    max: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def validate_bounds(self) -> "ConversionRateConfig":
        if self.min > self.base or self.base > self.max:
            raise ValueError("conversion rate bounds must satisfy min <= base <= max")
        return self


class ConversionMetricConfig(BaseModel):
    start_rate: ConversionRateConfig
    completion_rate: ConversionRateConfig


class ConversionRulesConfig(BaseModel):
    account_signups: ConversionMetricConfig
    newsletter_signups: ConversionMetricConfig


class ProjectConfig(BaseModel):
    project_name: str
    timezone: str = "UTC"
    start_date: date
    random_seed: int = 42
    base_daily_sessions: int = Field(gt=0)
    site: SiteConfig
    pages: list[PageConfig] = Field(min_length=1)
    countries: list[CountryConfig] = Field(min_length=1)
    devices: list[WeightedMultiplier] = Field(min_length=1)
    traffic_channels: list[TrafficChannelConfig] = Field(min_length=1)
    weekly_seasonality: dict[str, float]
    monthly_seasonality: dict[int, float]
    randomness: RandomnessConfig = Field(default_factory=RandomnessConfig)
    growth_trend: GrowthTrendConfig = Field(default_factory=GrowthTrendConfig)
    special_events: list[SpecialEventConfig] = Field(default_factory=list)
    metric_rules: MetricRulesConfig = Field(default_factory=MetricRulesConfig)
    conversion_rules: ConversionRulesConfig

    @field_validator("weekly_seasonality")
    @classmethod
    def validate_weekdays(cls, value: dict[str, float]) -> dict[str, float]:
        expected = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
        missing = expected - set(value)
        if missing:
            raise ValueError(f"weekly_seasonality missing: {', '.join(sorted(missing))}")
        return value

    @field_validator("monthly_seasonality")
    @classmethod
    def validate_months(cls, value: dict[int, float]) -> dict[int, float]:
        expected = set(range(1, 13))
        missing = expected - set(value)
        if missing:
            raise ValueError(f"monthly_seasonality missing months: {', '.join(map(str, sorted(missing)))}")
        return value


def load_config(path: str | Path | None = None) -> ProjectConfig:
    load_dotenv()
    config_path = Path(path or os.getenv("CONFIG_PATH", "config/project.yml"))
    with config_path.open("r", encoding="utf-8") as file:
        raw_config: dict[str, Any] = yaml.safe_load(file)
    return ProjectConfig.model_validate(raw_config)
