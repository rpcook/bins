# -------------- Standard libraries -----------------
import heapq
import threading
import time
from datetime import datetime, timedelta

# ---- GPIO library with mock for PC development ----
try:
    import RPi.GPIO as GPIO # type: ignore
except ImportError:
    from MockGPIO import MockGPIO
    GPIO = MockGPIO()

# ---------------- Custom Packages -------------------
import scraper
import webparser
from LEDcontroller import LEDcontroller
import LEDpatterns

# ------------- Configuration variables --------------
# TODO: read these in from config file
start_bin_schedule = 16 # 24 hour clock
stop_bin_schedule = 23 # 24 hour clock
web_scrape_schedule = 12 # 24 hour clock
bin_colours = {
    "black"  : (100,100,100), 
    "brown"  : (100, 38,  0),
    "blue"   : (  0,  0,100),
    "purple" : (100,  0,100)
    }

# ----------------- Global variables ------------------
date_information_int = []
bin_display_state = True
if datetime.now().hour >= start_bin_schedule and datetime.now().hour < stop_bin_schedule:
    bin_schedule_state = True
else:
    bin_schedule_state = False

# --------- User input control functions --------------
class button_handler:
    def __init__(self, PIN, single_fun=None, double_fun=None, long_fun=None, DOUBLE_TAP_TIME=0.3, LONG_HOLD_TIME=0.5):
        self.PIN = PIN
        self.DOUBLE_TAP_TIME = DOUBLE_TAP_TIME
        self.LONG_HOLD_TIME = LONG_HOLD_TIME
        self.last_press_time = 0
        self.press_time_start = 0
        self.single_timer = None
        self.single_handler = single_fun
        self.double_handler = double_fun
        self.long_handler = long_fun

    def button_pressed(self):
        press_time = time.monotonic()
        delta = press_time - self.last_press_time

        if delta < self.DOUBLE_TAP_TIME:
            if self.single_timer:
                self.single_timer.cancel()
            if self.double_handler:
                self.double_handler()
        else:
            self.press_start_time = press_time
            # schedule long-hold check
            threading.Timer(self.LONG_HOLD_TIME, self.check_hold, [press_time]).start()
            # schedule single-press detection unless another tap arrives
            self.single_timer = threading.Timer(self.DOUBLE_TAP_TIME, self.single_handler)
            if self.single_handler:
                self.single_timer.start()

        self.last_press_time = press_time

    def button_released(self):
        self.press_start_time = 0

    def check_hold(self, start_time):
        # if button still held after LONG_HOLD_TIME, it's a long hold
        if GPIO.input(self.PIN) == GPIO.HIGH and self.press_start_time == start_time:
            if self.long_handler:
                self.long_handler()

def toggle_bin_display():
    global bin_display_state
    bin_display_state = not bin_display_state
    update_bin_indicator()

def show_next_bin(sched):
    log_stuff("Double tap: show next bin collection")
    sched.statusLED.push_job("next_bin", 50, lambda led: LEDpatterns.solid_colour(led, (0,0,100)))
    time.sleep(1)
    sched.statusLED.remove_job("next_bin")

def soft_reset(sched):
    log_stuff("Long press: soft reset")
    sched.statusLED.push_job("soft_reset", 50, lambda led: LEDpatterns.solid_colour(led, (100,0,100)))
    time.sleep(1)
    sched.statusLED.remove_job("soft_reset")

# --------------------- Scheduler ---------------------
class Scheduler:
    def __init__(self, status_led_controller, bindicator_led_controller):
        self.events = []
        self.lock = threading.Lock()
        self.running = True
        self.statusLED = status_led_controller
        self.binLED = bindicator_led_controller

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

# -------------- Event Jobs ----------------
def heartbeat(sched):
    sched.statusLED.push_job("heartbeat", 1, lambda led: LEDpatterns.heartbeat(led))
    time.sleep(1)
    sched.statusLED.remove_job("heartbeat")
    # reschedule itself
    sched.schedule(datetime.now() + timedelta(seconds=10), heartbeat, sched)

def web_scrape(sched):
    global date_information_int
    sched.statusLED.push_job("web_scrape", 10, lambda led: LEDpatterns.web_activity(led))
    log_stuff("[Scraper] Starting web scrape...")
    try:
        with open("address.txt") as f:
            source = scraper.scrape_bin_date_website(f.readline())
        date_information_dict = webparser.parse_bin_table_to_dict(source)
        date_information_int = webparser.parse_dates(date_information_dict)
        log_stuff("[Scraper] Successfully finished web scrape.")
        sched.statusLED.push_job("success", 20, lambda led: LEDpatterns.success(led))
        # reschedule scraping for 12pm
        log_stuff("[Scraper] Rescheduling for 12pm")
        sched.schedule(next_schedule_time(web_scrape_schedule), web_scrape, sched)
    except:
        log_stuff("[Scraper] Fatal error in scraper")
        # reschedule for 10 minutes time
        log_stuff("[Scraper] Rescheduling for 10 minutes time")
        sched.schedule(datetime.now() + timedelta(minutes=10), web_scrape, sched)
    sched.statusLED.remove_job("web_scrape")

def show_bin_indicator(sched):
    global bin_schedule_state, bin_display_state
    bin_schedule_state = True
    bin_display_state = True
    update_bin_indicator()
    time.sleep(10)
    log_stuff("[Main] Bin indicator on for 4pm")
    sched.schedule(next_schedule_time(start_bin_schedule), show_bin_indicator, sched)

def hide_bin_indicator(sched):
    global bin_schedule_state
    bin_schedule_state = False
    update_bin_indicator()
    time.sleep(10)
    log_stuff("[Main] Bin indicator off at 11pm")
    sched.schedule(next_schedule_time(stop_bin_schedule), hide_bin_indicator, sched)

# ------- Helper functions --------
def POST(sched):
    # blink bin indicator, pretty rainbow and stuff
    pass

def next_schedule_time(hour):
    now = datetime.now()
    run_at = now.replace(hour=hour, minute=0, second=0)
    if run_at < now:
        run_at += timedelta(days=1)
    return run_at

def update_bin_indicator():
    if bin_display_state and bin_schedule_state:
        log_stuff("[Bin] Updating indicator illumination")
        if len(date_information_int) == 0:
            return
        today_int = datetime.now().date()
        for bin in bin_colours.keys():
            if (date_information_int[bin] - today_int).days == 1:
                sched.binLED.push_job("nextBin", 5, lambda led: LEDpatterns.solid_colour(led, bin_colours[bin]))
    else:
        log_stuff("[Bin] Turning off bin indicator")
        sched.binLED.remove_job("nextBin")

def check_scheduler(sched):
    # debug check
    for task in sched.events:
        print(task)

# ---------------- Main ----------------
if __name__ == "__main__":
    # --------------- Configure GPIO -------------------
    GPIO.setmode(GPIO.BCM) # BCM numbering

    # physical pin assignments
    BUTTON_PIN = 5
    STATUS_RED = 21
    STATUS_GREEN_BAR = 18
    STATUS_BLUE = 11
    BIN_RED = 10
    BIN_GREEN = 9
    BIN_BLUE = 17

    # button pin configuration
    GPIO.setup(BUTTON_PIN, GPIO.IN)
    
    # status LED configuration
    pins = (STATUS_RED, STATUS_GREEN_BAR, STATUS_BLUE)
    pwms = []
    for p in pins:
        GPIO.setup(p, GPIO.OUT)
        pwm = GPIO.PWM(p, 200)
        pwm.start(0)
        pwms.append(pwm)

    status_led = LEDcontroller(tuple(pwms), [False, True, False])

    # bin LED configuration
    pins = (BIN_RED, BIN_GREEN, BIN_BLUE)
    pwms = []
    for p in pins:
        GPIO.setup(p, GPIO.OUT)
        pwm = GPIO.PWM(p, 200)
        pwm.start(0)
        pwms.append(pwm)

    bin_led = LEDcontroller(tuple(pwms))

    sched = Scheduler(status_led, bin_led)

    # Kick off initial jobs
    sched.schedule(datetime.now() + timedelta(seconds=1), heartbeat, sched)
    sched.schedule(datetime.now() + timedelta(seconds=2), web_scrape, sched)
    sched.schedule(datetime.now() + timedelta(seconds=10), update_bin_indicator)

    # Schedule bin indicator illumination
    log_stuff("[Main] Bin indicator on for 4pm")
    sched.schedule(next_schedule_time(start_bin_schedule), show_bin_indicator, sched)
    log_stuff("[Main] Bin indicator off at 11pm")
    sched.schedule(next_schedule_time(stop_bin_schedule), hide_bin_indicator, sched)

    # set default bin illumination (off)
    sched.binLED.push_job("defaultOff", 1, lambda led: LEDpatterns.turn_off(led))

    # button listener
    # Set up event detection for rising / falling edges
    GPIO.add_event_detect(BUTTON_PIN, GPIO.BOTH, bouncetime=10)
    touch_button_handler = button_handler(PIN=BUTTON_PIN,
                                          single_fun=toggle_bin_display,
                                          double_fun=lambda: show_next_bin(sched),
                                          long_fun=lambda: soft_reset(sched))
    GPIO.add_event_callback(
        BUTTON_PIN,
        lambda: (
            touch_button_handler.button_pressed() if GPIO.input(BUTTON_PIN) == GPIO.HIGH else touch_button_handler.button_released()
        )
    )

    try:
        sched.run()
    except KeyboardInterrupt:
        sched.stop()
        GPIO.cleanup()
