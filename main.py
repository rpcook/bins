# -------------- Standard libraries -----------------
import heapq
import threading
import time
from datetime import datetime, timedelta
import RPi.GPIO as GPIO

# ---------------- Custom Packages -------------------
import scraper
import webparser

# ---------------- Global variables ----------------
date_information_int = []

# --------------- Configure GPIO -------------------
GPIO.setmode(GPIO.BCM)

STATUS_GREEN = 18

GPIO.setup(STATUS_GREEN, GPIO.OUT)

# ---------------- Status LED Manager ----------------
class statusLEDManager:
    def __init__(self):
        self.stack = []  # (priority, message)
        self.lock = threading.Lock()

    def push(self, priority, message):
        with self.lock:
            if not self.stack or priority >= self.stack[-1][0]:
                log_stuff(f"[LED] Pushed {message} (priority {priority})")
                self.stack.append((priority, message))
                self._update_led()
            else:
                log_stuff(f"[LED] Ignored {message} (priority {priority}) < current {self.stack[-1]}")

    def pop(self, message):
        with self.lock:
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][1] == message:
                    removed = self.stack.pop(i)
                    log_stuff(f"[LED] Popped {removed}")
                    break
            self._update_led()

    def _update_led(self):
        if self.stack:
            top = self.stack[-1]
            log_stuff(f"[LED] Active: {top[1]} (priority {top[0]})")
            # here you would actually set the GPIO LED
            GPIO.output(STATUS_GREEN, not GPIO.input(STATUS_GREEN))
        else:
            log_stuff("[LED] Off")

# ---------------- Scheduler ----------------
class Scheduler:
    def __init__(self, status_led_manager):
        self.events = []
        self.lock = threading.Lock()
        self.running = True
        self.statusLED = status_led_manager

    def schedule(self, when, func, *args, **kwargs):
        with self.lock:
            heapq.heappush(self.events, (when, func, args, kwargs))

    def stop(self):
        self.running = False

    def run(self):
        while self.running:
            now = datetime.now()
            job = None

            with self.lock:
                if self.events and self.events[0][0] <= now:
                    job = heapq.heappop(self.events)

            if job:
                _, func, args, kwargs = job
                threading.Thread(
                    target=func, args=args, kwargs=kwargs, daemon=True
                ).start()
            else:
                time.sleep(0.5)

# ---------------- Logging ----------------
def log_stuff(message):
    print(f"[{datetime.now()}] " + message)

# ---------------- Example Jobs ----------------
def heartbeat(sched):
    sched.statusLED.push(1, "Heartbeat")
    log_stuff("[LED] Heartbeat blink")
    time.sleep(0.2)
    sched.statusLED.pop("Heartbeat")
    # reschedule itself
    sched.schedule(datetime.now() + timedelta(seconds=3), heartbeat, sched)

def web_scrape(sched):
    global date_information_int
    sched.statusLED.push(5, "Web scrape running")
    log_stuff("[Scraper] Starting web scrape...")
    with open("address.txt") as f:
        source = scraper.scrape_bin_date_website(f.readline())
    date_information_dict = webparser.parse_bin_table_to_dict(source)
    date_information_int = webparser.parse_dates(date_information_dict)
    print(date_information_int)
    # time.sleep(5)
    log_stuff("[Scraper] Finished web scrape.")
    sched.statusLED.pop("Web scrape running")
    # schedule follow-up
    # sched.schedule(datetime.now() + timedelta(seconds=10), follow_up, sched)

def update_bin_indicator(sched):
    print(date_information_int)

def POST(sched):
    # blink bin indicator
    pass

def follow_up(sched):
    sched.statusLED.push(3, "Follow-up task")
    print(f"[{datetime.now()}] Running follow-up...")
    time.sleep(2)
    print(f"[{datetime.now()}] Follow-up done.")
    sched.statusLED.pop("Follow-up task")

# ---------------- Main ----------------
if __name__ == "__main__":
    statusLED = statusLEDManager()
    sched = Scheduler(statusLED)

    # Kick off initial jobs
    sched.schedule(datetime.now() + timedelta(seconds=1), heartbeat, sched)
    sched.schedule(datetime.now() + timedelta(seconds=2), web_scrape, sched)

    try:
        sched.run()
    except KeyboardInterrupt:
        sched.stop()
        GPIO.cleanup()
