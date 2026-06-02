from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from synthetic_analytics.config import ConversionMetricConfig, ProjectConfig
from synthetic_analytics.generator.time_series import (
    daily_noise_multiplier,
    event_multiplier,
    growth_multiplier,
    month_multiplier,
    random_noise_multiplier,
    stable_seed,
    weekday_multiplier,
)


GRAIN_COLUMNS = [
    "traffic_date",
    "site_name",
    "page_path",
    "page_type",
    "content_category",
    "phone_brand",
    "phone_model",
    "commercial_intent",
    "country",
    "region",
    "device_category",
    "traffic_source",
    "traffic_medium",
    "campaign",
]


def _weighted_share(item_weight: float, total_weight: float) -> float:
    return item_weight / total_weight if total_weight else 0


def _bounded_int(value: float, minimum: int = 0) -> int:
    return max(int(round(value)), minimum)


def _rate_noise(rng: np.random.Generator) -> float:
    return float(np.clip(rng.normal(loc=1.0, scale=0.10), 0.70, 1.30))


def _commercial_intent_multiplier(commercial_intent: str) -> float:
    return {
        "low": 0.75,
        "medium": 1.0,
        "high": 1.25,
        "very_high": 1.55,
    }[commercial_intent]


def _conversion_event_multiplier(
    config: ProjectConfig,
    traffic_date: date,
    page_type: str,
    content_category: str,
    phone_brand: str,
    country_name: str,
    source: str,
    field_name: str,
) -> float:
    multiplier = 1.0
    for event in config.special_events:
        if not (event.start_date <= traffic_date <= event.end_date):
            continue
        if event.page_types and page_type not in event.page_types:
            continue
        if event.content_categories and content_category not in event.content_categories:
            continue
        if event.phone_brands and phone_brand not in event.phone_brands:
            continue
        if event.countries and country_name not in event.countries:
            continue
        if event.channels and source not in event.channels:
            continue
        multiplier *= getattr(event, field_name)
    return multiplier


def _conversion_metrics(
    sessions: int,
    rules: ConversionMetricConfig,
    channel_multiplier: float,
    device_multiplier: float,
    page_multiplier: float,
    event_conversion_multiplier: float,
    rng: np.random.Generator,
) -> tuple[int, int]:
    start_rate = rules.start_rate.base
    start_rate *= channel_multiplier
    start_rate *= device_multiplier
    start_rate *= page_multiplier
    start_rate *= event_conversion_multiplier
    start_rate *= _rate_noise(rng)
    start_rate = float(np.clip(start_rate, rules.start_rate.min, rules.start_rate.max))

    completion_rate = rules.completion_rate.base
    completion_rate *= 0.85 + (channel_multiplier * 0.15)
    completion_rate *= _rate_noise(rng)
    completion_rate = float(
        np.clip(completion_rate, rules.completion_rate.min, rules.completion_rate.max)
    )

    starts = _bounded_int(sessions * start_rate)
    signups = min(starts, _bounded_int(starts * completion_rate))
    return starts, signups


def _metrics_for_sessions(
    sessions: int,
    config: ProjectConfig,
    rng: np.random.Generator,
    channel_medium: str,
    engagement_multiplier: float,
) -> dict[str, Any]:
    rules = config.metric_rules
    users_per_session = rng.uniform(rules.users_per_session_min, rules.users_per_session_max)
    users_count = min(sessions, _bounded_int(sessions * users_per_session, 1))

    new_user_rate = rng.uniform(rules.new_user_rate_min, rules.new_user_rate_max)
    if channel_medium in {"email", "none"}:
        new_user_rate *= 0.82
    elif channel_medium in {"paid_social", "referral"}:
        new_user_rate *= 1.08
    new_user_rate = float(np.clip(new_user_rate, 0.05, 0.95))

    new_users = min(users_count, _bounded_int(users_count * new_user_rate))
    returning_users = users_count - new_users

    pageviews_per_session = rng.uniform(
        rules.pageviews_per_session_min,
        rules.pageviews_per_session_max,
    )
    pageviews_per_session *= 0.9 + (engagement_multiplier * 0.1)
    pageviews = max(sessions, _bounded_int(sessions * pageviews_per_session))

    engagement_rate = float(
        rng.uniform(rules.engagement_rate_min, rules.engagement_rate_max)
    )
    engagement_rate *= engagement_multiplier
    engagement_rate = float(np.clip(engagement_rate, 0.05, 0.95))
    engaged_sessions = min(sessions, _bounded_int(sessions * engagement_rate))
    engagement_rate = round(engaged_sessions / sessions if sessions else 0, 4)
    bounce_rate = round(1 - engagement_rate, 4)

    avg_session_duration = int(
        rng.integers(
            rules.avg_session_duration_seconds_min,
            rules.avg_session_duration_seconds_max + 1,
        )
    )

    return {
        "sessions": sessions,
        "users_count": users_count,
        "new_users": new_users,
        "returning_users": returning_users,
        "pageviews": pageviews,
        "engaged_sessions": engaged_sessions,
        "avg_session_duration_seconds": avg_session_duration,
        "bounce_rate": bounce_rate,
        "engagement_rate": engagement_rate,
    }


def generate_daily_traffic(config: ProjectConfig, traffic_date: date) -> pd.DataFrame:
    page_weight = sum(item.traffic_weight for item in config.pages)
    country_weight = sum(item.weight for item in config.countries)
    device_weight = sum(item.weight for item in config.devices)
    channel_weight = sum(item.weight for item in config.traffic_channels)
    time_multiplier = (
        weekday_multiplier(config, traffic_date)
        * month_multiplier(config, traffic_date)
        * growth_multiplier(config, traffic_date)
        * daily_noise_multiplier(config, traffic_date)
    )

    rows: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for page in config.pages:
        for country in config.countries:
            for device in config.devices:
                for channel in config.traffic_channels:
                    rng = np.random.default_rng(
                        stable_seed(
                            config.random_seed,
                            traffic_date.isoformat(),
                            config.site.name,
                            page.page_path,
                            country.name,
                            device.name,
                            channel.source,
                            channel.medium,
                            channel.campaign,
                        )
                    )
                    share = (
                        _weighted_share(page.traffic_weight, page_weight)
                        * _weighted_share(country.weight, country_weight)
                        * _weighted_share(device.weight, device_weight)
                        * _weighted_share(channel.weight, channel_weight)
                    )
                    multiplier = (
                        country.multiplier
                        * device.multiplier
                        * channel.multiplier
                        * time_multiplier
                        * random_noise_multiplier(config, rng)
                        * event_multiplier(
                            config.special_events,
                            traffic_date,
                            page.page_type,
                            page.content_category,
                            page.phone_brand,
                            country.name,
                            channel.source,
                        )
                    )
                    sessions = _bounded_int(config.base_daily_sessions * share * multiplier, 1)
                    metrics = _metrics_for_sessions(
                        sessions,
                        config,
                        rng,
                        channel.medium,
                        page.engagement_multiplier,
                    )
                    account_signup_starts, account_signups = _conversion_metrics(
                        sessions=sessions,
                        rules=config.conversion_rules.account_signups,
                        channel_multiplier=(
                            channel.account_signup_multiplier
                            * page.account_signup_multiplier
                        ),
                        device_multiplier=device.multiplier,
                        page_multiplier=_commercial_intent_multiplier(page.commercial_intent),
                        event_conversion_multiplier=_conversion_event_multiplier(
                            config,
                            traffic_date,
                            page.page_type,
                            page.content_category,
                            page.phone_brand,
                            country.name,
                            channel.source,
                            "account_signup_multiplier",
                        ),
                        rng=rng,
                    )
                    newsletter_signup_starts, newsletter_signups = _conversion_metrics(
                        sessions=sessions,
                        rules=config.conversion_rules.newsletter_signups,
                        channel_multiplier=(
                            channel.newsletter_signup_multiplier
                            * page.newsletter_signup_multiplier
                        ),
                        device_multiplier=device.multiplier,
                        page_multiplier=_commercial_intent_multiplier(page.commercial_intent),
                        event_conversion_multiplier=_conversion_event_multiplier(
                            config,
                            traffic_date,
                            page.page_type,
                            page.content_category,
                            page.phone_brand,
                            country.name,
                            channel.source,
                            "newsletter_signup_multiplier",
                        ),
                        rng=rng,
                    )
                    rows.append(
                        {
                            "traffic_date": traffic_date,
                            "site_name": config.site.name,
                            "page_path": page.page_path,
                            "page_type": page.page_type,
                            "content_category": page.content_category,
                            "phone_brand": page.phone_brand or "none",
                            "phone_model": page.phone_model or "none",
                            "commercial_intent": page.commercial_intent,
                            "country": country.name,
                            "region": country.region or "Unknown",
                            "device_category": device.name,
                            "traffic_source": channel.source,
                            "traffic_medium": channel.medium,
                            "campaign": channel.campaign or "none",
                            **metrics,
                            "account_signup_starts": account_signup_starts,
                            "account_signups": account_signups,
                            "newsletter_signup_starts": newsletter_signup_starts,
                            "newsletter_signups": newsletter_signups,
                            "created_at": now,
                            "updated_at": now,
                        }
                    )

    return pd.DataFrame(rows)


def generate_date_range(config: ProjectConfig, start_date: date, end_date: date) -> pd.DataFrame:
    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date")
    frames = [
        generate_daily_traffic(config, item.date())
        for item in pd.date_range(start=start_date, end=end_date, freq="D")
    ]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
