from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from psycopg.sql import Identifier, SQL

from synthetic_analytics.database import connect


PROJECT_TABLES = [
    ("raw", "daily_traffic"),
    ("staging", "stg_daily_traffic"),
    ("marts", "mart_traffic_daily"),
    ("marts", "mart_traffic_summary"),
]

FILTER_COLUMNS = [
    "page_type",
    "content_category",
    "phone_brand",
    "phone_model",
    "commercial_intent",
    "country",
    "device_category",
    "traffic_source",
    "traffic_medium",
    "campaign",
]

RAW_COLUMNS = [
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
    "sessions",
    "users_count",
    "pageviews",
    "engaged_sessions",
    "bounce_rate",
    "engagement_rate",
    "account_signup_starts",
    "account_signups",
    "newsletter_signup_starts",
    "newsletter_signups",
]


@dataclass(frozen=True)
class TableRef:
    schema: str
    table: str

    @property
    def label(self) -> str:
        return f"{self.schema}.{self.table}"


def get_database_url() -> str | None:
    load_dotenv()
    return os.getenv("DATABASE_URL")


def run_query(query: SQL | str, params: Iterable[object] | None = None) -> pd.DataFrame:
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
    return pd.DataFrame(rows)


def table_exists(table_ref: TableRef) -> bool:
    query = """
        select exists (
            select 1
            from information_schema.tables
            where table_schema = %s
              and table_name = %s
        ) as exists
    """
    try:
        frame = run_query(query, (table_ref.schema, table_ref.table))
    except Exception:
        return False
    return bool(frame.iloc[0]["exists"]) if not frame.empty else False


def get_available_project_tables() -> list[str]:
    query = """
        select table_schema, table_name
        from information_schema.tables
        where (table_schema, table_name) in (
            ('raw', 'daily_traffic'),
            ('staging', 'stg_daily_traffic'),
            ('marts', 'mart_traffic_daily'),
            ('marts', 'mart_traffic_summary')
        )
        order by table_schema, table_name
    """
    return [
        f"{row.table_schema}.{row.table_name}"
        for row in run_query(query).itertuples(index=False)
    ]


@st.cache_data(ttl=60)
def load_raw_data() -> pd.DataFrame:
    table_ref = TableRef("raw", "daily_traffic")
    if not table_exists(table_ref):
        return pd.DataFrame()

    selected_columns = SQL(", ").join(Identifier(column) for column in RAW_COLUMNS)
    query = SQL("select {columns} from {schema}.{table} order by traffic_date desc").format(
        columns=selected_columns,
        schema=Identifier(table_ref.schema),
        table=Identifier(table_ref.table),
    )
    frame = run_query(query)
    if not frame.empty:
        frame["traffic_date"] = pd.to_datetime(frame["traffic_date"]).dt.date
    return frame


def filter_raw_data(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame

    min_date = frame["traffic_date"].min()
    max_date = frame["traffic_date"].max()
    selected_range = st.sidebar.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(selected_range, tuple) and len(selected_range) == 2:
        start_date, end_date = selected_range
    else:
        start_date, end_date = min_date, max_date

    filtered = frame[
        (frame["traffic_date"] >= start_date)
        & (frame["traffic_date"] <= end_date)
    ].copy()

    for column in FILTER_COLUMNS:
        values = sorted(frame[column].dropna().unique().tolist())
        selected = st.sidebar.multiselect(column, values, default=values)
        if selected:
            filtered = filtered[filtered[column].isin(selected)]

    return filtered


def metric_card(label: str, value: str) -> None:
    st.metric(label, value)


def format_int(value: float | int) -> str:
    return f"{int(value):,}"


def format_rate(value: float) -> str:
    return f"{value:.2%}"


def safe_rate(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def show_kpis(frame: pd.DataFrame) -> None:
    st.subheader("KPI Overview")
    if frame.empty:
        st.info("No raw traffic rows match the current filters.")
        return

    sessions = frame["sessions"].sum()
    users = frame["users_count"].sum()
    pageviews = frame["pageviews"].sum()
    engaged_sessions = frame["engaged_sessions"].sum()
    account_signups = frame["account_signups"].sum()
    newsletter_signups = frame["newsletter_signups"].sum()
    engagement_rate = safe_rate(engaged_sessions, sessions)
    bounce_rate = 1 - engagement_rate if sessions else 0

    values = [
        ("Sessions", format_int(sessions)),
        ("Users", format_int(users)),
        ("Pageviews", format_int(pageviews)),
        ("Engaged Sessions", format_int(engaged_sessions)),
        ("Engagement Rate", format_rate(engagement_rate)),
        ("Bounce Rate", format_rate(bounce_rate)),
        ("Account Signups", format_int(account_signups)),
        ("Newsletter Signups", format_int(newsletter_signups)),
        ("Account Signup Rate", format_rate(safe_rate(account_signups, sessions))),
        ("Newsletter Signup Rate", format_rate(safe_rate(newsletter_signups, sessions))),
    ]

    for row_start in range(0, len(values), 5):
        columns = st.columns(5)
        for column, (label, value) in zip(columns, values[row_start : row_start + 5]):
            with column:
                metric_card(label, value)


def show_line_chart(frame: pd.DataFrame, metric: str, title: str) -> None:
    daily = frame.groupby("traffic_date", as_index=False).agg(
        sessions=("sessions", "sum"),
        users_count=("users_count", "sum"),
        pageviews=("pageviews", "sum"),
        account_signups=("account_signups", "sum"),
        newsletter_signups=("newsletter_signups", "sum"),
        engaged_sessions=("engaged_sessions", "sum"),
    )
    daily["engagement_rate"] = daily["engaged_sessions"] / daily["sessions"]
    daily["bounce_rate"] = 1 - daily["engagement_rate"]
    fig = px.line(daily, x="traffic_date", y=metric, markers=True, title=title)
    st.plotly_chart(fig, width="stretch")


def show_time_series(frame: pd.DataFrame) -> None:
    st.subheader("Time Series")
    if frame.empty:
        st.info("No time series to show for the current filters.")
        return

    charts = [
        ("sessions", "Sessions by Date"),
        ("users_count", "Users by Date"),
        ("pageviews", "Pageviews by Date"),
        ("account_signups", "Account Signups by Date"),
        ("newsletter_signups", "Newsletter Signups by Date"),
        ("engagement_rate", "Engagement Rate by Date"),
        ("bounce_rate", "Bounce Rate by Date"),
    ]
    for left, right in zip(charts[::2], charts[1::2]):
        col1, col2 = st.columns(2)
        with col1:
            show_line_chart(frame, left[0], left[1])
        with col2:
            show_line_chart(frame, right[0], right[1])
    if len(charts) % 2:
        show_line_chart(frame, charts[-1][0], charts[-1][1])


def show_bar_chart(frame: pd.DataFrame, group_by: str | list[str], metric: str, title: str) -> None:
    grouped = frame.groupby(group_by, as_index=False)[metric].sum()
    if isinstance(group_by, list):
        grouped["label"] = grouped[group_by].agg(" / ".join, axis=1)
        x_axis = "label"
    else:
        x_axis = group_by
    grouped = grouped.sort_values(metric, ascending=False)
    fig = px.bar(grouped, x=x_axis, y=metric, title=title)
    st.plotly_chart(fig, width="stretch")


def show_top_bar_chart(
    frame: pd.DataFrame,
    group_by: str,
    metric: str,
    title: str,
    limit: int = 15,
) -> None:
    grouped = (
        frame.groupby(group_by, as_index=False)[metric]
        .sum()
        .sort_values(metric, ascending=False)
        .head(limit)
    )
    fig = px.bar(grouped, x=group_by, y=metric, title=title)
    st.plotly_chart(fig, width="stretch")


def show_rate_by_group(frame: pd.DataFrame, group_by: str, title: str) -> None:
    grouped = frame.groupby(group_by, as_index=False).agg(
        sessions=("sessions", "sum"),
        engaged_sessions=("engaged_sessions", "sum"),
    )
    grouped["engagement_rate"] = grouped["engaged_sessions"] / grouped["sessions"]
    grouped = grouped.sort_values("engagement_rate", ascending=False)
    fig = px.bar(grouped, x=group_by, y="engagement_rate", title=title)
    st.plotly_chart(fig, width="stretch")


def show_conversion_intent_chart(frame: pd.DataFrame) -> None:
    grouped = frame.groupby("commercial_intent", as_index=False).agg(
        account_signups=("account_signups", "sum"),
        newsletter_signups=("newsletter_signups", "sum"),
    )
    melted = grouped.melt(
        id_vars="commercial_intent",
        value_vars=["account_signups", "newsletter_signups"],
        var_name="conversion_type",
        value_name="conversions",
    )
    fig = px.bar(
        melted,
        x="commercial_intent",
        y="conversions",
        color="conversion_type",
        barmode="group",
        title="Conversions by Commercial Intent",
    )
    st.plotly_chart(fig, width="stretch")


def show_breakdowns(frame: pd.DataFrame) -> None:
    st.subheader("Breakdowns")
    if frame.empty:
        st.info("No breakdowns to show for the current filters.")
        return

    chart_specs = [
        ("page_type", "sessions", "Sessions by Page Type"),
        ("content_category", "sessions", "Sessions by Content Category"),
        ("page_type", "account_signups", "Account Signups by Page Type"),
        ("page_type", "newsletter_signups", "Newsletter Signups by Page Type"),
        ("phone_brand", "sessions", "Sessions by Phone Brand"),
        (["traffic_source", "traffic_medium"], "sessions", "Sessions by Source / Medium"),
    ]
    for left, right in zip(chart_specs[::2], chart_specs[1::2]):
        col1, col2 = st.columns(2)
        with col1:
            show_bar_chart(frame, left[0], left[1], left[2])
        with col2:
            show_bar_chart(frame, right[0], right[1], right[2])

    col1, col2 = st.columns(2)
    with col1:
        show_top_bar_chart(frame, "page_path", "sessions", "Top 15 Pages by Sessions")
    with col2:
        show_rate_by_group(frame, "page_type", "Engagement Rate by Page Type")
    show_conversion_intent_chart(frame)


def show_data_quality(frame: pd.DataFrame) -> None:
    st.subheader("Data Quality Checks")
    if frame.empty:
        st.info("No rows available for validation.")
        return

    checks = {
        "site_name not null": frame["site_name"].notna() & (frame["site_name"] != ""),
        "page_path not null": frame["page_path"].notna() & (frame["page_path"] != ""),
        "page_type not null": frame["page_type"].notna() & (frame["page_type"] != ""),
        "content_category not null": (
            frame["content_category"].notna() & (frame["content_category"] != "")
        ),
        "commercial_intent accepted values": frame["commercial_intent"].isin(
            ["low", "medium", "high", "very_high"]
        ),
        "sessions >= 0": frame["sessions"] >= 0,
        "users_count >= 0": frame["users_count"] >= 0,
        "pageviews >= sessions": frame["pageviews"] >= frame["sessions"],
        "engaged_sessions <= sessions": frame["engaged_sessions"] <= frame["sessions"],
        "account_signups <= account_signup_starts": (
            frame["account_signups"] <= frame["account_signup_starts"]
        ),
        "newsletter_signups <= newsletter_signup_starts": (
            frame["newsletter_signups"] <= frame["newsletter_signup_starts"]
        ),
        "engagement_rate between 0 and 1": frame["engagement_rate"].between(0, 1),
        "bounce_rate between 0 and 1": frame["bounce_rate"].between(0, 1),
    }
    results = pd.DataFrame(
        [
            {
                "check": name,
                "passed_rows": int(mask.sum()),
                "failed_rows": int((~mask).sum()),
                "status": "Pass" if bool(mask.all()) else "Fail",
            }
            for name, mask in checks.items()
        ]
    )
    st.dataframe(results, width="stretch", hide_index=True)


def show_model_preview() -> None:
    st.subheader("dbt Model Preview")
    options = [
        TableRef("staging", "stg_daily_traffic"),
        TableRef("marts", "mart_traffic_daily"),
        TableRef("marts", "mart_traffic_summary"),
    ]
    selected_label = st.selectbox("Model", [option.label for option in options])
    selected = next(option for option in options if option.label == selected_label)

    if not table_exists(selected):
        st.info(f"`{selected.label}` is not available yet. Run `dbt build` to create dbt models.")
        return

    count_query = SQL("select count(*) as row_count from {schema}.{table}").format(
        schema=Identifier(selected.schema),
        table=Identifier(selected.table),
    )
    preview_query = SQL("select * from {schema}.{table} limit 500").format(
        schema=Identifier(selected.schema),
        table=Identifier(selected.table),
    )
    row_count = int(run_query(count_query).iloc[0]["row_count"])
    st.write(f"Rows: {row_count:,}")
    st.dataframe(run_query(preview_query), width="stretch")


def show_database_status() -> bool:
    st.subheader("Database Status")
    database_url = get_database_url()
    st.write(f"DATABASE_URL configured: {'Yes' if database_url else 'No'}")
    if not database_url:
        st.warning("Add DATABASE_URL to `.env` or your shell environment.")
        return False

    try:
        available_tables = get_available_project_tables()
    except Exception as exc:
        st.error(
            "Connection failed. If the database is dormant, it may need a short wake-up window. "
            "Refresh the app after a few seconds."
        )
        st.exception(exc)
        return False

    st.success("Connection works.")
    if available_tables:
        st.write("Available project tables:")
        st.write(", ".join(f"`{table}`" for table in available_tables))
    else:
        st.info("No project tables found yet. Run `init-db`, generate data, and run dbt build.")
    return True


def main() -> None:
    st.set_page_config(
        page_title="Synthetic Web Analytics Data Explorer",
        layout="wide",
    )
    st.title("Synthetic Web Analytics Data Explorer")
    st.caption(
        "Inspect generated traffic, engagement, and conversion metrics from the synthetic analytics pipeline."
    )

    connected = show_database_status()
    if not connected:
        return

    try:
        raw_frame = load_raw_data()
    except Exception as exc:
        st.error(
            "Could not load the page-level raw table. If this database still has the old brand-level "
            "schema, drop and recreate `raw.daily_traffic`, then regenerate data."
        )
        st.exception(exc)
        show_model_preview()
        return
    if raw_frame.empty:
        st.info("`raw.daily_traffic` is not available or has no rows. Run `init-db` and generate data.")
        show_model_preview()
        return

    st.sidebar.header("Filters")
    filtered = filter_raw_data(raw_frame)
    show_kpis(filtered)
    show_time_series(filtered)
    show_breakdowns(filtered)

    st.subheader("Data Preview")
    st.dataframe(filtered.head(500), width="stretch")

    show_model_preview()
    show_data_quality(filtered)


if __name__ == "__main__":
    main()
