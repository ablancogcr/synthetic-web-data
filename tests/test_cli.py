import argparse

from synthetic_analytics import cli


def test_railway_start_exits_without_pipeline_by_default(monkeypatch) -> None:
    called = False

    def fake_run_pipeline(_: argparse.Namespace) -> None:
        nonlocal called
        called = True

    monkeypatch.delenv("RUN_DAILY_PIPELINE_ON_START", raising=False)
    monkeypatch.setattr(cli, "handle_run_pipeline", fake_run_pipeline)

    cli.handle_railway_start(argparse.Namespace(dbt_project_dir="dbt_analytics"))

    assert called is False


def test_railway_start_runs_pipeline_when_enabled(monkeypatch) -> None:
    captured_args = None

    def fake_run_pipeline(args: argparse.Namespace) -> None:
        nonlocal captured_args
        captured_args = args

    monkeypatch.setenv("RUN_DAILY_PIPELINE_ON_START", "true")
    monkeypatch.setattr(cli, "handle_run_pipeline", fake_run_pipeline)

    cli.handle_railway_start(argparse.Namespace(dbt_project_dir="dbt_analytics"))

    assert captured_args is not None
    assert captured_args.mode == "daily"
    assert captured_args.date is None
