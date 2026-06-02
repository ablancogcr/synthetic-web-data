from __future__ import annotations

import argparse
import os
import subprocess
from datetime import date, timedelta

from dotenv import load_dotenv

from synthetic_analytics.config import load_config
from synthetic_analytics.database import dbt_env_from_database_url, init_database, upsert_daily_traffic
from synthetic_analytics.generator.daily_traffic import generate_daily_traffic, generate_date_range


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def resolve_generation_dates(args: argparse.Namespace) -> tuple[date, date]:
    if args.mode == "backfill":
        if not args.start_date or not args.end_date:
            raise SystemExit("--start-date and --end-date are required for backfill mode")
        return args.start_date, args.end_date

    target_date = args.date or (date.today() - timedelta(days=1))
    return target_date, target_date


def handle_init_db(_: argparse.Namespace) -> None:
    init_database()
    print("Initialized raw.daily_traffic")


def handle_generate(args: argparse.Namespace) -> int:
    config = load_config(args.config_path)
    start_date, end_date = resolve_generation_dates(args)
    frame = (
        generate_daily_traffic(config, start_date)
        if start_date == end_date
        else generate_date_range(config, start_date, end_date)
    )
    rows = upsert_daily_traffic(frame)
    print(f"Generated and upserted {rows} rows for {start_date} to {end_date}")
    return rows


def run_dbt_build(project_dir: str) -> None:
    profiles_dir = os.getenv("DBT_PROFILES_DIR", "dbt_analytics")
    target = os.getenv("DBT_TARGET", "dev")
    command = [
        "dbt",
        "build",
        "--project-dir",
        project_dir,
        "--profiles-dir",
        profiles_dir,
        "--target",
        target,
    ]
    env = os.environ.copy()
    env.update(dbt_env_from_database_url())
    subprocess.run(command, check=True, env=env)


def handle_dbt_build(args: argparse.Namespace) -> None:
    run_dbt_build(args.dbt_project_dir)


def handle_run_pipeline(args: argparse.Namespace) -> None:
    handle_generate(args)
    run_dbt_build(args.dbt_project_dir)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Synthetic web analytics pipeline")
    parser.add_argument("--config-path", default=None, help="Path to config/project.yml")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_db = subparsers.add_parser("init-db", help="Create raw schema and daily traffic table")
    init_db.set_defaults(func=handle_init_db)

    dbt_build = subparsers.add_parser("dbt-build", help="Run dbt build without generating data")
    dbt_build.add_argument("--dbt-project-dir", default="dbt_analytics")
    dbt_build.set_defaults(func=handle_dbt_build)

    for name in ("generate", "run-pipeline"):
        command = subparsers.add_parser(name)
        command.add_argument("--mode", choices=["daily", "backfill"], required=True)
        command.add_argument("--date", type=parse_date, help="Specific daily generation date")
        command.add_argument("--start-date", type=parse_date, help="Backfill start date")
        command.add_argument("--end-date", type=parse_date, help="Backfill end date")
        command.set_defaults(func=handle_generate if name == "generate" else handle_run_pipeline)
        if name == "run-pipeline":
            command.add_argument("--dbt-project-dir", default="dbt_analytics")

    return parser


def main() -> None:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
