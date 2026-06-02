from datetime import date

from synthetic_analytics.config import load_config
from synthetic_analytics.generator.daily_traffic import GRAIN_COLUMNS, generate_daily_traffic
from synthetic_analytics.generator.time_series import daily_noise_multiplier


CONVERSION_COLUMNS = [
    "account_signup_starts",
    "account_signups",
    "newsletter_signup_starts",
    "newsletter_signups",
]

PAGE_COLUMNS = [
    "site_name",
    "page_path",
    "page_type",
    "content_category",
    "phone_brand",
    "phone_model",
    "commercial_intent",
]


def test_generate_daily_traffic_shape() -> None:
    config = load_config("config/project.yml")
    frame = generate_daily_traffic(config, date(2025, 1, 15))

    expected_rows = (
        len(config.pages)
        * len(config.countries)
        * len(config.devices)
        * len(config.traffic_channels)
    )
    assert len(frame) == expected_rows
    for column in GRAIN_COLUMNS:
        assert column in frame.columns
    for column in CONVERSION_COLUMNS:
        assert column in frame.columns
    for column in PAGE_COLUMNS:
        assert column in frame.columns


def test_generated_metrics_are_consistent() -> None:
    config = load_config("config/project.yml")
    frame = generate_daily_traffic(config, date(2025, 11, 28))

    assert (frame["users_count"] <= frame["sessions"]).all()
    assert (frame["new_users"] + frame["returning_users"] == frame["users_count"]).all()
    assert (frame["pageviews"] >= frame["sessions"]).all()
    assert (frame["engaged_sessions"] <= frame["sessions"]).all()
    assert (frame["avg_session_duration_seconds"] > 0).all()
    assert (frame[CONVERSION_COLUMNS] >= 0).all().all()
    assert (frame["account_signups"] <= frame["account_signup_starts"]).all()
    assert (frame["newsletter_signups"] <= frame["newsletter_signup_starts"]).all()


def test_generated_rates_are_bounded() -> None:
    config = load_config("config/project.yml")
    frame = generate_daily_traffic(config, date(2025, 5, 20))

    assert frame["bounce_rate"].between(0, 1).all()
    assert frame["engagement_rate"].between(0, 1).all()


def test_generated_conversion_rates_are_realistic() -> None:
    config = load_config("config/project.yml")
    frame = generate_daily_traffic(config, date(2025, 11, 28))

    account_start_rate = frame["account_signup_starts"].sum() / frame["sessions"].sum()
    newsletter_start_rate = frame["newsletter_signup_starts"].sum() / frame["sessions"].sum()
    account_completion_rate = frame["account_signups"] / frame["account_signup_starts"].replace(0, 1)
    newsletter_completion_rate = frame["newsletter_signups"] / frame["newsletter_signup_starts"].replace(0, 1)

    assert 0 < account_start_rate <= config.conversion_rules.account_signups.start_rate.max
    assert 0 < newsletter_start_rate <= config.conversion_rules.newsletter_signups.start_rate.max
    assert account_completion_rate.between(0, 1).all()
    assert newsletter_completion_rate.between(0, 1).all()


def test_generated_pages_come_from_config() -> None:
    config = load_config("config/project.yml")
    frame = generate_daily_traffic(config, date(2025, 5, 20))
    configured_paths = {page.page_path for page in config.pages}

    assert set(frame["page_path"]).issubset(configured_paths)
    assert frame["site_name"].eq(config.site.name).all()
    assert frame["commercial_intent"].isin(["low", "medium", "high", "very_high"]).all()


def test_generation_is_deterministic_for_same_date() -> None:
    config = load_config("config/project.yml")

    first = generate_daily_traffic(config, date(2025, 5, 20)).drop(columns=["created_at", "updated_at"])
    second = generate_daily_traffic(config, date(2025, 5, 20)).drop(columns=["created_at", "updated_at"])

    assert first.equals(second)


def test_daily_noise_is_stable_but_varies_by_date() -> None:
    config = load_config("config/project.yml")

    jan_2_first = daily_noise_multiplier(config, date(2025, 1, 2))
    jan_2_second = daily_noise_multiplier(config, date(2025, 1, 2))
    jan_3 = daily_noise_multiplier(config, date(2025, 1, 3))

    assert jan_2_first == jan_2_second
    assert jan_2_first != jan_3
    assert config.randomness.daily_min_multiplier <= jan_2_first <= config.randomness.daily_max_multiplier
