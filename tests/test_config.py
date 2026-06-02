from synthetic_analytics.config import load_config


def test_load_default_config() -> None:
    config = load_config("config/project.yml")

    assert config.project_name == "phonescope_web_analytics_demo"
    assert config.site.name == "PhoneScope"
    assert config.site.domain == "phonescope.example"
    assert len(config.pages) >= 25
    assert len(config.countries) == 5
    assert len(config.devices) == 3
    assert len(config.traffic_channels) == 5
    assert len(config.special_events) >= 2
    assert config.weekly_seasonality["monday"] > config.weekly_seasonality["sunday"]
    assert config.conversion_rules.account_signups.start_rate.base == 0.035
    assert config.conversion_rules.newsletter_signups.completion_rate.base == 0.72
    assert config.traffic_channels[0].account_signup_multiplier > 0
    assert all(page.page_path.startswith("/") for page in config.pages)
    assert {page.page_type for page in config.pages} >= {
        "home",
        "review",
        "comparison",
        "guide",
        "deals",
        "discount_club_landing",
        "newsletter_landing",
        "phone_listing",
        "phone_profile",
        "carrier",
        "news",
    }
