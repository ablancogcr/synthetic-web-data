from __future__ import annotations

from datetime import date

import numpy as np

from synthetic_analytics.config import ProjectConfig, SpecialEventConfig


def stable_seed(base_seed: int, *parts: object) -> int:
    text = "|".join(str(part) for part in (base_seed, *parts))
    value = 0
    for char in text:
        value = (value * 131 + ord(char)) % (2**32)
    return value


def weekday_multiplier(config: ProjectConfig, traffic_date: date) -> float:
    return config.weekly_seasonality[traffic_date.strftime("%A").lower()]


def month_multiplier(config: ProjectConfig, traffic_date: date) -> float:
    return config.monthly_seasonality[traffic_date.month]


def growth_multiplier(config: ProjectConfig, traffic_date: date) -> float:
    months_since_start = (traffic_date.year - config.start_date.year) * 12 + (
        traffic_date.month - config.start_date.month
    )
    return (1 + config.growth_trend.monthly_growth_rate) ** max(months_since_start, 0)


def random_noise_multiplier(config: ProjectConfig, rng: np.random.Generator) -> float:
    noise = rng.normal(loc=1.0, scale=config.randomness.noise_stddev)
    return float(np.clip(noise, config.randomness.min_multiplier, config.randomness.max_multiplier))


def daily_noise_multiplier(config: ProjectConfig, traffic_date: date) -> float:
    rng = np.random.default_rng(stable_seed(config.random_seed, traffic_date.isoformat(), "daily_noise"))
    noise = rng.normal(loc=1.0, scale=config.randomness.daily_noise_stddev)
    return float(
        np.clip(
            noise,
            config.randomness.daily_min_multiplier,
            config.randomness.daily_max_multiplier,
        )
    )


def event_multiplier(
    events: list[SpecialEventConfig],
    traffic_date: date,
    page_type: str,
    content_category: str,
    phone_brand: str,
    country: str,
    source: str,
) -> float:
    multiplier = 1.0
    for event in events:
        if not (event.start_date <= traffic_date <= event.end_date):
            continue
        if event.page_types and page_type not in event.page_types:
            continue
        if event.content_categories and content_category not in event.content_categories:
            continue
        if event.phone_brands and phone_brand not in event.phone_brands:
            continue
        if event.countries and country not in event.countries:
            continue
        if event.channels and source not in event.channels:
            continue
        multiplier *= event.multiplier
    return multiplier
