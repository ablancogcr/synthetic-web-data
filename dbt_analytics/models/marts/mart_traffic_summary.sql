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
    round(sum(pageviews)::numeric / nullif(sum(sessions), 0), 4) as pageviews_per_session,
    round(sum(engaged_sessions)::numeric / nullif(sum(sessions), 0), 4) as engagement_rate,
    round(1 - (sum(engaged_sessions)::numeric / nullif(sum(sessions), 0)), 4) as bounce_rate,
    round(sum(new_users)::numeric / nullif(sum(users_count), 0), 4) as new_user_rate,
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
group by traffic_date, site_name, page_type, content_category
