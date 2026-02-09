import unittest
from datetime import datetime

from app.core.scheduler import Scheduler


class SchedulerTest(unittest.TestCase):
    def test_run_pending_executes_job(self):
        hits = {"count": 0}

        def job():
            hits["count"] += 1

        scheduler = Scheduler()
        scheduler.add_daily_job("test", "00:00", job, run_in_thread=False)
        scheduler._jobs[0].next_run = datetime.now()
        scheduler.run_pending()

        self.assertEqual(hits["count"], 1)


if __name__ == "__main__":
    unittest.main()
