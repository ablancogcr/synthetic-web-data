with aggregated as (
    select
        traffic_date,
        site_name,
        page_path,
        page_type,
        content_category,
        phone_brand,
        phone_model,
        commercial_intent,
        country,
        device_category,
        traffic_source,
        traffic_medium,
        sum(sessions) as sessions,
        sum(users_count) as users_count,
        sum(new_users) as new_users,
        sum(returning_users) as returning_users,
        sum(pageviews) as pageviews,
        sum(engaged_sessions) as engaged_sessions,
        sum(account_signup_starts) as account_signup_starts,
        sum(account_signups) as account_signups,
        sum(newsletter_signup_starts) as newsletter_signup_starts,
        sum(newsletter_signups) as newsletter_signups,
        sum(avg_session_duration_seconds * sessions) as weighted_session_duration
    from {{ ref('stg_daily_traffic') }}
    group by
        traffic_date,
        site_name,
        page_path,
        page_type,
        content_category,
        phone_brand,
        phone_model,
        commercial_intent,
        country,
        device_category,
        traffic_source,
        traffic_medium
),

metrics as (
    select
        *,
        coalesce(round(pageviews::numeric / nullif(sessions, 0), 4), 0) as pageviews_per_session,
        coalesce(round(engaged_sessions::numeric / nullif(sessions, 0), 4), 0) as engagement_rate,
        coalesce(round(account_signups::numeric / nullif(sessions, 0), 4), 0) as account_signup_rate,
        coalesce(
            round(account_signups::numeric / nullif(account_signup_starts, 0), 4),
            0
        ) as account_signup_completion_rate,
        coalesce(
            round(newsletter_signups::numeric / nullif(sessions, 0), 4),
            0
        ) as newsletter_signup_rate,
        coalesce(
            round(newsletter_signups::numeric / nullif(newsletter_signup_starts, 0), 4),
            0
        ) as newsletter_signup_completion_rate,
        coalesce(
            round(weighted_session_duration::numeric / nullif(sessions, 0), 2),
            0
        ) as avg_session_duration_seconds
    from aggregated
)

select
    md5({{ dbt.concat([
        "traffic_date::text",
        "'|'",
        "site_name",
        "'|'",
        "page_path",
        "'|'",
        "page_type",
        "'|'",
        "content_category",
        "'|'",
        "phone_brand",
        "'|'",
        "phone_model",
        "'|'",
        "commercial_intent",
        "'|'",
        "country",
        "'|'",
        "device_category",
        "'|'",
        "traffic_source",
        "'|'",
        "traffic_medium"
    ]) }}) as mart_traffic_daily_key,
    traffic_date,
    site_name,
    page_path,
    page_type,
    content_category,
    phone_brand,
    phone_model,
    commercial_intent,
    country,
    device_category,
    traffic_source,
    traffic_medium,
    sessions,
    users_count,
    new_users,
    returning_users,
    pageviews,
    engaged_sessions,
    account_signup_starts,
    account_signups,
    newsletter_signup_starts,
    newsletter_signups,
    pageviews_per_session,
    engagement_rate,
    round(1 - engagement_rate, 4) as bounce_rate,
    account_signup_rate,
    account_signup_completion_rate,
    newsletter_signup_rate,
    newsletter_signup_completion_rate,
    avg_session_duration_seconds
from metrics
