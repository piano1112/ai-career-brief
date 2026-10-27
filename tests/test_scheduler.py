from app.agents.background.scheduler import build_scheduler


def test_scheduler_uses_seoul_timezone_and_has_heartbeat() -> None:
    scheduler = build_scheduler()
    assert str(scheduler.timezone) == "Asia/Seoul"
    assert [job.id for job in scheduler.get_jobs()] == ["heartbeat"]
