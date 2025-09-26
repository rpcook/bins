# -------------- Standard libraries -----------------
import heapq
import threading
import time
from datetime import datetime, timedelta

# ---- GPIO library with mock for PC development ----
try:
    import RPi.GPIO as GPIO
except ImportError:
    class MockGPIO:
        BCM = "BCM"
        OUT = "OUT"
        HIGH = 1
        LOW = 0

        def setmode(self, mode): print(f"[MockGPIO] setmode({mode})")
        def setup(self, pin, mode): print(f"[MockGPIO] setup(pin={pin}, mode={mode})")
        def output(self, pin, state): print(f"[MockGPIO] output(pin={pin}, state={state})")
        def cleanup(self): print("[MockGPIO] cleanup()")
        def input(self, pin): print(f"[MockGPIO] output(pin={pin})")

    GPIO = MockGPIO()

# ---------------- Custom Packages -------------------
import scraper
import webparser

# ---------------- Global variables ----------------
date_information_int = []
bin_display_state = True
bin_schedule_state = True

# --------------- Configure GPIO -------------------
GPIO.setmode(GPIO.BCM) # BCM numbering

BUTTON_PIN = 5
STATUS_GREEN_BAR = 18
BIN_RED = 10
BIN_GREEN = 9
BIN_BLUE = 17


GPIO.setup(BUTTON_PIN, GPIO.IN)
GPIO.setup(STATUS_GREEN_BAR, GPIO.OUT)
GPIO.setup(BIN_RED, GPIO.OUT)
GPIO.setup(BIN_GREEN, GPIO.OUT)
GPIO.setup(BIN_BLUE, GPIO.OUT)

r = GPIO.PWM(BIN_RED, 200)
g = GPIO.PWM(BIN_GREEN, 200)
b = GPIO.PWM(BIN_BLUE, 200)
r.start(0)
g.start(0)
b.start(0)

# ---------------- Status LED Manager ----------------
class statusLEDManager:
    def __init__(self):
        self.stack = []  # (priority, message)
        self.lock = threading.Lock()

    def push(self, priority, message):
        with self.lock:
            if not self.stack or priority >= self.stack[-1][0]:
                # log_stuff(f"[LED] Pushed {message} (priority {priority})")
                self.stack.append((priority, message))
                self._update_led()
            else:
                log_stuff(f"[LED] Ignored {message} (priority {priority}) < current {self.stack[-1]}")

    def pop(self, message):
        with self.lock:
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][1] == message:
                    removed = self.stack.pop(i)
                    # log_stuff(f"[LED] Popped {removed}")
                    break
            self._update_led()

    def _update_led(self):
        if self.stack:
            top = self.stack[-1]
            # log_stuff(f"[LED] Active: {top[1]} (priority {top[0]})")
            # here you would actually set the GPIO LED
            GPIO.output(STATUS_GREEN_BAR, False)
            time.sleep(0.05)
            GPIO.output(STATUS_GREEN_BAR, True)
        else:
            # log_stuff("[LED] Off")
            pass

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
    # log_stuff("[LED] Heartbeat blink")
    time.sleep(0.2)
    sched.statusLED.pop("Heartbeat")
    # reschedule itself
    sched.schedule(datetime.now() + timedelta(seconds=10), heartbeat, sched)

def web_scrape(sched):
    global date_information_int
    sched.statusLED.push(5, "Web scrape running")
    log_stuff("[Scraper] Starting web scrape...")
    try:
        with open("address.txt") as f:
            source = scraper.scrape_bin_date_website(f.readline())
        date_information_dict = webparser.parse_bin_table_to_dict(source)
        date_information_int = webparser.parse_dates(date_information_dict)
        print(date_information_int)
        # time.sleep(5)
        log_stuff("[Scraper] Successfully finished web scrape.")
        # reschedule scraping for 12pm
        log_stuff("[Scraper] Rescheduling for 12pm")
        sched.schedule(next_schedule_time(12), web_scrape, sched)
    except:
        log_stuff("[Scraper] Fatal error in scraper")
        # reschedule for 10 minutes time
        log_stuff("[Scraper] Rescheduling for 10 minutes time")
        sched.schedule(datetime.now() + timedelta(minutes=10), web_scrape, sched)
    sched.statusLED.pop("Web scrape running")
    # schedule follow-up
    # sched.schedule(datetime.now() + timedelta(seconds=10), follow_up, sched)

def show_bin_indicator(sched):
    global bin_schedule_state
    bin_schedule_state = True
    update_bin_indicator()
    # print(date_information_int)

def hide_bin_indicator(sched):
    global bin_schedule_state
    bin_schedule_state = False
    update_bin_indicator()
    # print(date_information_int)

def POST(sched):
    # blink bin indicator
    pass

# def follow_up(sched):
#     sched.statusLED.push(3, "Follow-up task")
#     print(f"[{datetime.now()}] Running follow-up...")
#     time.sleep(2)
#     print(f"[{datetime.now()}] Follow-up done.")
#     sched.statusLED.pop("Follow-up task")

# ------- Helper functions --------
def next_schedule_time(hour):
    now = datetime.now()
    run_at = now.replace(hour=hour, minute=0, second=0)
    if run_at < now:
        run_at += timedelta(days=1)
    return run_at

def button_pressed():
    global bin_display_state
    bin_display_state = not bin_display_state
    update_bin_indicator()
    log_stuff("button pressed")

def update_bin_indicator():
    if bin_display_state and bin_schedule_state:
        log_stuff("[Bin] Updating indicator illumination")
    else:
        log_stuff("[Bin] Turning off bin indicator")

# ---------------- Main ----------------
if __name__ == "__main__":
    statusLED = statusLEDManager()
    sched = Scheduler(statusLED)

    # Kick off initial jobs
    sched.schedule(datetime.now() + timedelta(seconds=1), heartbeat, sched)
    sched.schedule(datetime.now() + timedelta(seconds=2), web_scrape, sched)

    # Schedule bin indicator illumination
    log_stuff("[Main] Bin indicator on for 4pm")
    sched.schedule(next_schedule_time(16), show_bin_indicator, sched)
    log_stuff("[Main] Bin indicator off at 11pm")
    sched.schedule(next_schedule_time(16), hide_bin_indicator, sched)

    # button listener
    # Set up event detection for both edges
    GPIO.add_event_detect(BUTTON_PIN, GPIO.RISING, bouncetime=10)

    GPIO.add_event_callback(BUTTON_PIN, lambda ch: button_pressed())

    try:
        sched.run()
    except KeyboardInterrupt:
        sched.stop()
        r.stop()
        g.stop()
        b.stop()
        GPIO.cleanup()
