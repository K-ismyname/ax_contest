# APScheduler로 daily_graph를 매일 오전 7시에 실행한다.

from datetime import date
from apscheduler.schedulers.blocking import BlockingScheduler

import sys
sys.path.insert(0, "src")

from lovebug_alert.rag.graph import build_daily_graph

daily_graph = build_daily_graph()


def run_daily():
    today = date.today().isoformat()
    print(f"[daily_graph] {today} 실행 시작")
    result = daily_graph.invoke({
        "date": today,
        "weather_today": {}, "observations_today": [],
        "current_dd": 0.0, "reports_today": [],
        "risk_level": "정상", "rag_summary": "",
        "email_sent": False, "report": {},
        "citizen_answer": "", "map_path": "",
    })
    print(f"[daily_graph] 완료 — 경보: {result['risk_level']}, DD: {result['current_dd']:.1f}")


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="Asia/Seoul")
    scheduler.add_job(run_daily, "cron", hour=7, minute=0)
    print("스케줄러 시작 (매일 07:00 KST)")
    scheduler.start()
