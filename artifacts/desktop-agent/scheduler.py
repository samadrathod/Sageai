"""
scheduler.py — Scheduled morning and evening news briefings.
"""

from __future__ import annotations
import datetime
import time
import threading
import logging
from local_commands.automation_commands import handle_global_news_briefing

logger = logging.getLogger("sage-agent")


class DailyScheduler:
    def __init__(self):
        self.running = False
        self.thread = None
        self.last_run_key = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        logger.info("SAGE background scheduler started.")

    def stop(self):
        self.running = False

    def _loop(self):
        while self.running:
            now = datetime.datetime.now()
            # Morning briefing: 8:00 AM. Evening briefing: 7:00 PM (19:00)
            target_hours = [8, 19]

            if now.hour in target_hours and now.minute == 0:
                run_key = f"{now.date()}_{now.hour}"
                if self.last_run_key != run_key:
                    self.last_run_key = run_key
                    logger.info(f"Triggering scheduled briefing for {now.hour}:00...")
                    # Trigger briefing in a separate thread so it doesn't block
                    briefing_thread = threading.Thread(
                        target=self._run_briefing,
                        daemon=True
                    )
                    briefing_thread.start()

            # Check every 30 seconds
            time.sleep(30)

    def _run_briefing(self):
        try:
            logger.info("Running scheduled global news briefing...")
            handle_global_news_briefing(None, {})
        except Exception as e:
            logger.error(f"Error in scheduled news briefing: {e}")


# Global instance
scheduler = DailyScheduler()
