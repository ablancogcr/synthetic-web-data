with aggregated as (
    select
        traffic_date,
        site_name,
        page_type,
        content_category,
        sum(sessions) as total_sessions,
        sum(users_count) as total_users,
        sum(new_users) as total_new_users,
        sum(returning_users) as total_returning_users,
        sum(pageviews) as total_pageviews,
        sum(engaged_sessions) as total_engaged_sessions,
        sum(account_signup_starts) as total_account_signup_starts,
        sum(account_signups) as total_account_signups,
        sum(newsletter_signup_starts) as total_newsletter_signup_starts,
        sum(newsletter_signups) as total_newsletter_signups,
        sum(avg_session_duration_seconds * sessions) as weighted_session_duration
    from {{ ref('stg_daily_traffic') }}
    group by
        traffic_date,
        site_name,
        page_type,
        content_category
),

metrics as (
    select
        *,
        coalesce(round(total_pageviews::numeric / nullif(total_sessions, 0), 4), 0) as pageviews_per_session,
        coalesce(round(total_engaged_sessions::numeric / nullif(total_sessions, 0), 4), 0) as engagement_rate,
        coalesce(round(total_new_users::numeric / nullif(total_users, 0), 4), 0) as new_user_rate,
        coalesce(
            round(total_account_signups::numeric / nullif(total_sessions, 0), 4),
            0
        ) as account_signup_rate,
        coalesce(
            round(total_account_signups::numeric / nullif(total_account_signup_starts, 0), 4),
            0
        ) as account_signup_completion_rate,
        coalesce(
            round(total_newsletter_signups::numeric / nullif(total_sessions, 0), 4),
            0
        ) as newsletter_signup_rate,
        coalesce(
            round(total_newsletter_signups::numeric / nullif(total_newsletter_signup_starts, 0), 4),
            0
        ) as newsletter_signup_completion_rate,
        coalesce(
            round(weighted_session_duration::numeric / nullif(total_sessions, 0), 2),
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
        "page_type",
        "'|'",
        "content_category"
    ]) }}) as mart_traffic_summary_key,
    traffic_date,
    site_name,
    page_type,
    content_category,
    total_sessions,
    total_users,
    total_new_users,
    total_returning_users,
    total_pageviews,
    total_engaged_sessions,
    total_account_signup_starts,
    total_account_signups,
    total_newsletter_signup_starts,
    total_newsletter_signups,
    pageviews_per_session,
    engagement_rate,
    round(1 - engagement_rate, 4) as bounce_rate,
    new_user_rate,
    account_signup_rate,
    account_signup_completion_rate,
    newsletter_signup_rate,
    newsletter_signup_completion_rate,
    avg_session_duration_seconds
from metrics
