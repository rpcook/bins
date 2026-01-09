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
# TODO: read these in from TOML config file
start_bin_schedule = 16 # 24 hour clock
stop_bin_schedule = 23 # 24 hour clock
web_scrape_schedule = 12 # 24 hour clock
bin_colours = {
    "black"  : (100,100,100), 
    "brown"  : (100, 38,  0),
    "blue"   : (  0,  0,100),
    "purple" : (100,  0,100)
    }

# ---------- User input control class ---------------
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

    def edge_detected(self, channel):
        if GPIO.input(channel) == GPIO.HIGH:
            self.button_pressed()
        else:
            self.button_released()
    
    def button_pressed(self):
        press_time = time.monotonic()
        delta = press_time - self.last_press_time

        if delta < self.DOUBLE_TAP_TIME:
            if self.single_timer:
                self.single_timer.cancel()
            if self.double_handler:
                log_stuff("Double tap.")
                self.double_handler()
        else:
            self.press_start_time = press_time
            # schedule long-hold check
            threading.Timer(self.LONG_HOLD_TIME, self.check_hold, [press_time]).start()
            # schedule single-press detection unless another tap arrives
            self.single_timer = threading.Timer(self.DOUBLE_TAP_TIME, self.single_hander_wrapper)
            if self.single_handler:
                self.single_timer.start()

        self.last_press_time = press_time

    def single_hander_wrapper(self):
        log_stuff("Single tap.")
        self.single_handler()

    def button_released(self):
        self.press_start_time = 0

    def check_hold(self, start_time):
        # if button still held after LONG_HOLD_TIME, it's a long hold
        if GPIO.input(self.PIN) == GPIO.HIGH and self.press_start_time == start_time:
            if self.long_handler:
                log_stuff("Long press.")
                self.long_handler()

# -------------- Scheduler class---------------------
class Scheduler:
    def __init__(self, status_led_controller, bindicator_led_controller, binSched):
        self.events = []
        self.lock = threading.Lock()
        self.running = True
        self.statusLED = status_led_controller
        self.binLED = bindicator_led_controller
        self.binSched = binSched

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
    # TODO: actual logging to file
    print(f"[{datetime.now()}] " + message)

# -------------- Event Jobs ----------------
def heartbeat(sched):
    # TODO: check health of scheduler
    sched.statusLED.push_job("heartbeat", 1, lambda led: LEDpatterns.heartbeat(led))
    time.sleep(1)
    sched.statusLED.remove_job("heartbeat")
    # reschedule itself
    sched.schedule(datetime.now() + timedelta(seconds=10), heartbeat, sched)

def soft_reset(sched):
    log_stuff("Soft reset.")
    # TODO: perform reset of scheduler / bindicator etc, POST again
    binIndicator.reset() # reset status of bin indicator
    # reset scheduler queue
    # assign start-up jobs to scheduler queue
    # POST bindicator
    POST(sched)
    sched.statusLED.push_job("soft_reset", 50, lambda led: LEDpatterns.solid_colour(led, (100,0,100)))
    time.sleep(1)
    sched.statusLED.remove_job("soft_reset")
    LEDpatterns.turn_off(sched.statusLED)

class binSchedule: # class container for the web-scraper
    def __init__(self):
        self.date_information_int = []
    
    def web_scrape(self, sched):
        sched.statusLED.push_job("web_scrape", 10, lambda led: LEDpatterns.web_activity(led))
        log_stuff("[Scraper] Starting web scrape...")
        try:
            with open("address.txt") as f:
                source = scraper.scrape_bin_date_website(f.readline())
            date_information_dict = webparser.parse_bin_table_to_dict(source)
            self.date_information_int = webparser.parse_dates(date_information_dict)
            log_stuff("[Scraper] Successfully finished web scrape.")
            sched.statusLED.push_job("success", 20, lambda led: LEDpatterns.success(led))
            # reschedule scraping for 12pm
            log_stuff("[Scraper] Rescheduling for 12pm")
            sched.schedule(next_schedule_time(web_scrape_schedule), sched.binSched.web_scrape, sched)
        except:
            log_stuff("[Scraper] Fatal error in scraper")
            # reschedule for 10 minutes time
            log_stuff("[Scraper] Rescheduling for 10 minutes time")
            sched.schedule(datetime.now() + timedelta(minutes=10), sched.binSched.web_scrape, sched)
        sched.statusLED.remove_job("web_scrape")
    
    def getBinDates(self):
        return self.date_information_int

def show_next_bin(sched):
    log_stuff("Show next bin collection.")
    date_information = sched.binSched.getBinDates()
    if len(date_information) == 0:
        # if there's no bin information, show error on status LED
        sched.statusLED.push_job("error", 50, lambda led: LEDpatterns.error(led))
        return
    today_int = datetime.now().date()
    next_bin_int = 100
    next_bin_key = []
    for bin in bin_colours.keys():
        if (date_information[bin] - today_int).days < next_bin_int:
            # loop over dictionary of bin dates and collect next closest
            next_bin_int = (date_information[bin] - today_int).days
            next_bin_key = bin
    # call next bin indicator function (solid for 1s, then flash according to number of days until collection)
    sched.binLED.push_job("user_request_next_bin", 50, lambda led: LEDpatterns.next_bin(led, bin_colours[next_bin_key], next_bin_int))

class binIndicatorController: # class container for the bin indicator LED controller functions
    def __init__(self):
        self.reset()

    def reset(self):
        self.bin_display_state = True
        if datetime.now().hour >= start_bin_schedule and datetime.now().hour < stop_bin_schedule:
            self.bin_schedule_state = True
        else:
            self.bin_schedule_state = False

    def show_bin_indicator(self, sched):
        self.bin_schedule_state = True
        self.bin_display_state = True
        self.update_bin_indicator(sched)
        time.sleep(10)
        log_stuff("[Main] Bin indicator on for 4pm")
        sched.schedule(next_schedule_time(start_bin_schedule), self.show_bin_indicator, sched)

    def hide_bin_indicator(self, sched):
        self.bin_schedule_state = False
        self.update_bin_indicator(sched)
        time.sleep(10)
        log_stuff("[Main] Bin indicator off at 11pm")
        sched.schedule(next_schedule_time(stop_bin_schedule), self.hide_bin_indicator, sched)

    def toggle_bin_display(self, sched):
        self.bin_display_state = not self.bin_display_state
        self.update_bin_indicator(sched)

    def update_bin_indicator(self, sched):
        if self.bin_display_state and self.bin_schedule_state:
            date_information = sched.binSched.getBinDates()
            log_stuff("[Bin] Updating indicator illumination")
            if len(date_information) == 0:
                return
            today_int = datetime.now().date()
            for bin in bin_colours.keys():
                if (date_information[bin] - today_int).days == 1:
                    sched.binLED.push_job("scheduled_next_bin", 5, lambda led: LEDpatterns.solid_colour(led, bin_colours[bin]))
        else:
            log_stuff("[Bin] Turning off bin indicator")
            sched.binLED.remove_job("scheduled_next_bin")

# ------- Helper functions --------
def POST(sched):
    for h in range(180, 481+360, 2):
        RGB = HSVtoRGB(h, 1, 1)
        sched.binLED.push_job("POST", 50, lambda led: LEDpatterns.solid_colour(led, RGB))
        time.sleep(0.02)
    time.sleep(2)
    sched.binLED.remove_job("POST")

def HSVtoRGB(hue, saturation, value):
    maxRGB = 100
    chroma = value * saturation
    X = chroma * (1 - abs((hue / 60) % 2 - 1))
    m = value - chroma
    sector = int(hue // 60) % 6
    rgb_table = [
        (chroma, X, 0),  # 0 ≤ H < 60
        (X, chroma, 0),  # 60 ≤ H < 120
        (0, chroma, X),  # 120 ≤ H < 180
        (0, X, chroma),  # 180 ≤ H < 240
        (X, 0, chroma),  # 240 ≤ H < 300
        (chroma, 0, X),  # 300 ≤ H < 360
    ]
    RGB = (rgb_table[sector])
    R = (RGB[0] + m) * maxRGB
    G = (RGB[1] + m) * maxRGB
    B = (RGB[2] + m) * maxRGB
    return (R, G, B)

def next_schedule_time(hour):
    now = datetime.now()
    run_at = now.replace(hour=hour, minute=0, second=0)
    if run_at < now:
        run_at += timedelta(days=1)
    return run_at

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

    # instantiate binSchedule class
    binSched = binSchedule()

    # instantiate scheduler class
    sched = Scheduler(status_led, bin_led, binSched)

    # instantiate binIndicatorController
    binIndicator = binIndicatorController()

    # Kick off initial jobs
    sched.schedule(datetime.now() + timedelta(seconds=1), heartbeat, sched)
    sched.schedule(datetime.now() + timedelta(seconds=0.9), POST, sched)
    sched.schedule(datetime.now() + timedelta(seconds=2), binSched.web_scrape, sched)
    sched.schedule(datetime.now() + timedelta(seconds=10), binIndicator.update_bin_indicator, sched)

    # Schedule bin indicator illumination
    log_stuff("[Main] Bin indicator on for 4pm")
    sched.schedule(next_schedule_time(start_bin_schedule), binIndicator.show_bin_indicator, sched)
    log_stuff("[Main] Bin indicator off at 11pm")
    sched.schedule(next_schedule_time(stop_bin_schedule), binIndicator.hide_bin_indicator, sched)

    # set default bin illumination (off)
    sched.binLED.push_job("defaultOff", 1, lambda led: LEDpatterns.turn_off(led))

    # button listener
    # Set up event detection for rising / falling edges
    GPIO.add_event_detect(BUTTON_PIN, GPIO.BOTH, bouncetime=10)
    touch_button_handler = button_handler(PIN=BUTTON_PIN,
                                          single_fun=lambda: binIndicator.toggle_bin_display(sched),
                                          double_fun=lambda: show_next_bin(sched),
                                          long_fun=lambda: soft_reset(sched))
    GPIO.add_event_callback(BUTTON_PIN, touch_button_handler.edge_detected)

    try:
        sched.run()
    except KeyboardInterrupt:
        sched.stop()
        GPIO.cleanup()
