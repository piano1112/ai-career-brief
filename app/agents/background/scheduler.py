"""백그라운드 에이전트의 스케줄 정의.

job은 여기 한 곳에 모아서 "언제 무엇이 도는지"를 한눈에 볼 수 있게 한다.
(Milestone 5에서 collect_rss, publish_briefing 등이 추가된다 — SPEC 5.3)
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler

from app.agents.background.jobs.heartbeat import heartbeat
from app.config import get_settings


def build_scheduler() -> BlockingScheduler:
    tz = ZoneInfo(get_settings().tz)
    scheduler = BlockingScheduler(
        timezone=tz,
        job_defaults={
            # worker가 잠깐 멈췄다 살아나도 밀린 실행을 한꺼번에 몰아서 돌리지 않는다.
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 60 * 5,
        },
    )
    # next_run_time=now: 시작 직후 한 번 바로 실행해서, 1분을 기다리지 않고도 동작을 확인한다.
    scheduler.add_job(
        heartbeat, "interval", minutes=1, id="heartbeat", next_run_time=datetime.now(tz)
    )
    return scheduler
