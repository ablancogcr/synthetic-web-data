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
    round(sum(pageviews)::numeric / nullif(sum(sessions), 0), 4) as pageviews_per_session,
    round(sum(engaged_sessions)::numeric / nullif(sum(sessions), 0), 4) as engagement_rate,
    round(1 - (sum(engaged_sessions)::numeric / nullif(sum(sessions), 0)), 4) as bounce_rate,
    round(sum(account_signups)::numeric / nullif(sum(sessions), 0), 4) as account_signup_rate,
    round(
        sum(account_signups)::numeric / nullif(sum(account_signup_starts), 0),
        4
    ) as account_signup_completion_rate,
    round(
        sum(newsletter_signups)::numeric / nullif(sum(sessions), 0),
        4
    ) as newsletter_signup_rate,
    round(
        sum(newsletter_signups)::numeric / nullif(sum(newsletter_signup_starts), 0),
        4
    ) as newsletter_signup_completion_rate,
    round(
        sum(avg_session_duration_seconds * sessions)::numeric / nullif(sum(sessions), 0),
        2
    ) as avg_session_duration_seconds
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
