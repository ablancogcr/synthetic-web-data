with source as (
    select *
    from {{ source('raw', 'daily_traffic') }}
),

cleaned as (
    select
        id,
        traffic_date::date as traffic_date,
        coalesce(nullif(trim(site_name), ''), 'PhoneScope') as site_name,
        trim(page_path) as page_path,
        lower(trim(page_type)) as page_type,
        lower(trim(content_category)) as content_category,
        coalesce(nullif(trim(phone_brand), ''), 'none') as phone_brand,
        coalesce(nullif(trim(phone_model), ''), 'none') as phone_model,
        lower(trim(commercial_intent)) as commercial_intent,
        trim(country) as country,
        coalesce(nullif(trim(region), ''), 'Unknown') as region,
        lower(trim(device_category)) as device_category,
        lower(trim(traffic_source)) as traffic_source,
        lower(trim(traffic_medium)) as traffic_medium,
        coalesce(nullif(lower(trim(campaign)), ''), 'none') as campaign,
        sessions::integer as sessions,
        users_count::integer as users_count,
        new_users::integer as new_users,
        returning_users::integer as returning_users,
        pageviews::integer as pageviews,
        engaged_sessions::integer as engaged_sessions,
        avg_session_duration_seconds::integer as avg_session_duration_seconds,
        bounce_rate::numeric as bounce_rate,
        engagement_rate::numeric as engagement_rate,
        account_signup_starts::integer as account_signup_starts,
        account_signups::integer as account_signups,
        newsletter_signup_starts::integer as newsletter_signup_starts,
        newsletter_signups::integer as newsletter_signups,
        created_at,
        updated_at
    from source
)

select
    {{ dbt.concat([
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
        "region",
        "'|'",
        "device_category",
        "'|'",
        "traffic_source",
        "'|'",
        "traffic_medium",
        "'|'",
        "campaign"
    ]) }} as daily_traffic_key,
    *
from cleaned
