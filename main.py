# -------------- Standard libraries -----------------
import heapq
import threading
import time
from datetime import datetime, timedelta
import tomllib
import logging
from logging.handlers import TimedRotatingFileHandler
import os

# ---- GPIO library with mock for PC development ----
try:
    LOG_PATH = "/home/pi/logs/" # default log path (assumes Linux / RPi)
    import RPi.GPIO as GPIO # type: ignore
except ImportError:
    LOG_PATH = "./logs/"
    from MockGPIO import MockGPIO
    GPIO = MockGPIO()

# ---------------- Custom Packages -------------------
import scraper
import webparser
from LEDcontroller import LEDcontroller
import LEDpatterns

# ------------- Configuration variables --------------
with open("config.toml", "rb") as f:
    config = tomllib.load(f)

START_BIN_SCHEDULE = config["display_on"]
STOP_BIN_SCHEDULE = config["display_off"]
WEB_SCRAPE_SCHEDULE = config["poll_web"]

BIN_COLOURS = {k: tuple(v) for k, v in config["bin_colours"].items()}

SHORT_TIMEOUT = config["short_timeout"]
LONG_TIMEOUT = config["long_timeout"]

#TODO: debug elevation:
#  - extra-long press to enable debug for TIMEOUT
#  - entering alert (error) state enables debug for SHORTTIMEOUT
#  - poll in heartbeat for presence of file in some tempfs folder, then enable debug for TIMEOUT, delete the temp trigger file
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
                logger.info("Double tap.")
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
        logger.info("Single tap.")
        self.single_handler()

    def button_released(self):
        self.press_start_time = 0

    def check_hold(self, start_time):
        # if button still held after LONG_HOLD_TIME, it's a long hold
        if GPIO.input(self.PIN) == GPIO.HIGH and self.press_start_time == start_time:
            if self.long_handler:
                logger.info("Long press.")
                self.long_handler()

# -------------- Scheduler class---------------------
class Scheduler:
    def __init__(self, status_led_controller, bindicator_led_controller, binSched, binIndicator):
        self.events = []
        self.lock = threading.Lock()
        self.running = True
        self.statusLED = status_led_controller
        self.binLED = bindicator_led_controller
        self.binSched = binSched
        self.binIndicator = binIndicator

    def schedule(self, when, func, *args, **kwargs):
        logger.debug("Scheduler adding job.")
        with self.lock:
            heapq.heappush(self.events, (when, func, args, kwargs))

    def stop(self):
        logger.debug("Scheduler stopping.")
        self.running = False

    def clearHeap(self):
        logger.debug("Scheduler clearing heap")
        with self.lock:
            for _ in range(len(self.events)):
                heapq.heappop(self.events)

    def run(self):
        while self.running:
            now = datetime.now()
            job = None

            with self.lock:
                if self.events and self.events[0][0] <= now:
                    job = heapq.heappop(self.events)

            if job:
                _, func, args, kwargs = job
                logger.debug("Scheduler launching job.")
                threading.Thread(
                    target=func, args=args, kwargs=kwargs, daemon=True
                ).start()
            else:
                time.sleep(0.5)

# ---------------- Logging ----------------
logger = logging.getLogger(__name__)
def setup_logging():
    LOG_LEVEL = logging.INFO
    handler = TimedRotatingFileHandler(
        filename=LOG_PATH + "bin.log",
        when="midnight",       # rotate daily
        interval=1,
        backupCount=180,         # keep ~6 months
        encoding="utf-8",
        utc=False
    )

    handler.suffix = "%Y-%m-%d"

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s: %(message)s"
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)
    root.addHandler(handler)

# -------------- Event Jobs ----------------
class Chest: 
    # class that contains the heartbeat
    def __init__(self):
        self.heartbeatAlertLevel = 0
        self.longDebug = False

    def heartbeat(self, sched):
        # Check health of schedulers
        logger.debug("Hearbeat.")
        # check for filesystem trigger for debug mode
        if os.path.exists("~/logs/debug"):
            self.longDebug = True
            os.remove("~/logs/debug")
            logging.getLogger().setLevel(logging.DEBUG)
            logger.debug("Entering debug logging from filesystem trigger.")
            sched.schedule(datetime.now() + timedelta(minutes=LONG_TIMEOUT), revertLoggingLevel, sched)

        oldAlertLevel = self.heartbeatAlertLevel
        self.heartbeatAlertLevel = 0
        ## check application health
        # check if date information is available
        logger.debug("Length of bin date dictionary: %d", len(sched.binSched.getBinDates()))
        if len(sched.binSched.getBinDates()) == 0:
            # no available date information
            self.heartbeatAlertLevel = 1
        # check job queue lengths
        scheulerQueueLength = len(sched.events)
        statusLEDqueueLength = len(sched.statusLED.jobs)
        binLEDqueueLength = len(sched.binLED.jobs)
        logger.debug("Queue lengths: %d %d %d", scheulerQueueLength, statusLEDqueueLength, binLEDqueueLength)
        if (scheulerQueueLength <= 1 or 
            scheulerQueueLength > 10 or
            statusLEDqueueLength > 10 or
            binLEDqueueLength > 10):
            # job queue is either too empty or is filling up
            self.heartbeatAlertLevel = 2
        # call heartbeat LED pattern
        logger.debug("Application alert level: %d", self.heartbeatAlertLevel)
        sched.statusLED.push_job("heartbeat", 1, lambda led: LEDpatterns.heartbeat(led, self.heartbeatAlertLevel))
        if (self.heartbeatAlertLevel > oldAlertLevel) and not (self.longDebug):
            # alert level has increased, set logger level to debug for short period of time.
            logger.warning("System Alert Level has increased to Level %d, entering debug logging for short period.", self.heartbeatAlertLevel)
            logging.getLogger().setLevel(logging.DEBUG)
            sched.schedule(datetime.now() + timedelta(minutes=SHORT_TIMEOUT), revertLoggingLevel, sched)
        # reschedule itself
        time.sleep(1)
        sched.schedule(datetime.now() + timedelta(seconds=10), self.heartbeat, sched)

def soft_reset(sched):
    logger.info("Soft reset.")
    sched.statusLED.push_job("reset", 70, lambda led: LEDpatterns.solid_colour(led, (20,0,0)))
    time.sleep(1)
    sched.statusLED.remove_job("reset")
    sched.binIndicator.reset() # reset status of bin indicator
    # reset scheduler queue
    sched.clearHeap()
    sched.statusLED.clear_jobs()
    sched.binLED.clear_jobs()
    # assign start-up jobs to scheduler queue
    set_initial_jobs(sched)

class binSchedule: # class container for the web-scraper
    def __init__(self):
        self.date_information_int = {}
    
    def web_scrape(self, sched):
        sched.statusLED.push_job("web_scrape", 10, lambda led: LEDpatterns.web_activity(led))
        logger.info("Starting web scrape.")
        try:
            with open("address.txt") as f:
                source = scraper.scrape_bin_date_website(f.readline())
            date_information_dict = webparser.parse_bin_table_to_dict(source)
            self.date_information_int = webparser.parse_dates(date_information_dict)
            del self.date_information_int["Brown caddy"] # remove the food waste caddy from dictionary
            logger.info("Successfully finished web scrape.")
            sched.statusLED.push_job("success", 20, lambda led: LEDpatterns.success(led))
            # reschedule scraping for 12pm
            logger.info("Rescheduling for web scrape for next scheduled time (%d00).", WEB_SCRAPE_SCHEDULE)
            sched.schedule(next_schedule_time(WEB_SCRAPE_SCHEDULE), sched.binSched.web_scrape, sched)
        except:
            logger.error("Fatal error in scraper.")
            sched.statusLED.push_job("error", 40, lambda led: LEDpatterns.error(led))
            # reschedule for 10 minutes time
            logger.info("Rescheduling web scrape for 30 minutes time.")
            sched.schedule(datetime.now() + timedelta(minutes=30), sched.binSched.web_scrape, sched)
        sched.statusLED.remove_job("web_scrape")
    
    def getNextBin(self):
        # return list of next bins (to handle corner case of two bins on same day)
        today_int = datetime.now().date()
        orderedBins = {k: (v-today_int).days for k, v in sorted(self.date_information_int.items(), key=lambda item: (item[1]-today_int).days)}
        return orderedBins

    def getBinDates(self):
        return self.date_information_int

def show_next_bin(sched):
    logger.info("Show next bin collection.")
    date_information = sched.binSched.getBinDates()
    if len(date_information) == 0:
        # if there's no bin information, show error on status LED
        sched.statusLED.push_job("error", 50, lambda led: LEDpatterns.error(led))
        return
    orderedBinDict = sched.binSched.getNextBin()
    keyList = list(orderedBinDict)
    if orderedBinDict[keyList[0]] == orderedBinDict[keyList[1]]:
        # if the first two bins fall on the same day
        logger.info("Two bins falling on same day.")
        logger.info("Next bin is %r, in %d day(s).", keyList[1], orderedBinDict[keyList[1]])
        # display the second bin colour for 2s, 0.5s off
        sched.binLED.push_job("second_bin", 50, lambda led: LEDpatterns.solid_colour(led, BIN_COLOURS[keyList[1]]))
        time.sleep(2)
        sched.binLED.remove_job("second_bin")
        time.sleep(0.5)
    # display the first bin using the standard pattern of solid then flash
    logger.info("Next bin is %r in %d day(s).", keyList[0], orderedBinDict[keyList[0]])
    sched.binLED.push_job("user_request_next_bin", 50, lambda led: LEDpatterns.next_bin(led, BIN_COLOURS[keyList[0]], orderedBinDict[keyList[0]]))

class binIndicatorController: # class container for the bin indicator LED controller functions
    def __init__(self):
        self.reset()
        self.secondBinSameDayDisplay = False
        self.secondBinSameDayLogged = False

    def reset(self):
        self.bin_display_state = True
        if datetime.now().hour >= START_BIN_SCHEDULE and datetime.now().hour < STOP_BIN_SCHEDULE:
            self.bin_schedule_state = True
        else:
            self.bin_schedule_state = False

    def show_bin_indicator(self, sched):
        logger.info("Scheduled start time for display.")
        self.bin_schedule_state = True
        self.bin_display_state = True
        self.secondBinSameDayLogged = False
        self.update_bin_indicator(sched)
        time.sleep(10)
        logger.info("Added scheduled ON time for Bin Indicator to scheduler (%d00).", START_BIN_SCHEDULE)
        sched.schedule(next_schedule_time(START_BIN_SCHEDULE), self.show_bin_indicator, sched)

    def hide_bin_indicator(self, sched):
        logger.info("Scheduled stop time for display")
        self.bin_schedule_state = False
        self.update_bin_indicator(sched)
        time.sleep(10)
        logger.info("Added scheduled OFF time for Bin Indicator to scheduler (%d00).", STOP_BIN_SCHEDULE)
        sched.schedule(next_schedule_time(STOP_BIN_SCHEDULE), self.hide_bin_indicator, sched)

    def toggle_bin_display(self, sched):
        self.bin_display_state = not self.bin_display_state
        self.update_bin_indicator(sched)

    def update_bin_indicator(self, sched):
        if self.bin_display_state and self.bin_schedule_state:
            # if we're in the display time window and the display hasn't been disabled by user input
            date_information = sched.binSched.getBinDates()
            if len(date_information) == 0:
                # cancel display update if no date information available
                return
            
            orderedBinDict = sched.binSched.getNextBin()
            keyList = list(orderedBinDict)
            if (orderedBinDict[keyList[0]] == orderedBinDict[keyList[1]]) and (orderedBinDict[keyList[0]] == 1):
                # if there are two bins on same day
                if not self.secondBinSameDayLogged:
                    logger.info("Two bins on same day. Toggling between bins every 10s.")
                    logger.info("Bin name: %r, RGB assigned: %d, %d, %d", keyList[0], BIN_COLOURS[keyList[0]][0], BIN_COLOURS[keyList[0]][1], BIN_COLOURS[keyList[0]][2])
                    logger.info("Bin name: %r, RGB assigned: %d, %d, %d", keyList[1], BIN_COLOURS[keyList[1]][0], BIN_COLOURS[keyList[1]][1], BIN_COLOURS[keyList[1]][2])
                    self.secondBinSameDayLogged = True
                try:
                    # remove the previous bin display to stop job queue growing uncontrollably
                    sched.binLED.remove_job("scheduled_next_bin")
                finally:
                    # update the bin indicator LED
                    sched.binLED.push_job("scheduled_next_bin", 5, lambda led: LEDpatterns.solid_colour(led, BIN_COLOURS[keyList[0 if self.secondBinSameDayDisplay else 1]]))
                    # toggle the second bin display flag
                    self.secondBinSameDayDisplay = not self.secondBinSameDayDisplay
                    # reschedule this job for 10s time
                    sched.schedule(datetime.now() + timedelta(seconds=10), sched.binIndicator.update_bin_indicator, sched)
            elif (orderedBinDict[keyList[0]] == 1):
                sched.binLED.push_job("scheduled_next_bin", 5, lambda led: LEDpatterns.solid_colour(led, BIN_COLOURS[keyList[0]]))
                logger.info("Updating Bin Indicator illumination.")
                logger.info("Bin name: %r, RGB assigned: %d, %d, %d", keyList[0], BIN_COLOURS[keyList[0]][0], BIN_COLOURS[keyList[0]][1], BIN_COLOURS[keyList[0]][2])
            else:
                logger.info("No bin due tomorrow.")
        else:
            logger.info("Turning off Bin Indicator.")
            sched.binLED.remove_job("scheduled_next_bin")

# ------- Helper functions --------
def revertLoggingLevel():
    chest.longDebug = False
    logging.getLogger().setLevel(logging.INFO)

def POST(sched):
    for h in range(180, 481+360, 2):
        RGB = HSVtoRGB(h, 1, 1)
        sched.binLED.push_job("POST", 50, lambda led: LEDpatterns.solid_colour(led, RGB))
        time.sleep(0.01)
    sched.binLED.push_job("success", 60, lambda led: LEDpatterns.success(led, 100))
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

def set_initial_jobs(sched):
    sched.schedule(datetime.now() + timedelta(seconds=1), chest.heartbeat, sched)
    logger.info("Added Heartbeat to scheduler.")
    sched.schedule(datetime.now() + timedelta(seconds=0.9), POST, sched)
    logger.info("Added POST to scheduler.")
    sched.schedule(datetime.now() + timedelta(seconds=6), sched.binSched.web_scrape, sched)
    logger.info("Added Web Scrape to scheduler.")
    sched.schedule(datetime.now() + timedelta(seconds=14), sched.binIndicator.update_bin_indicator, sched)
    logger.info("Added Update Bin Indicator to scheduler.")

    # Schedule bin indicator illumination
    sched.schedule(next_schedule_time(START_BIN_SCHEDULE), sched.binIndicator.show_bin_indicator, sched)
    logger.info("Added scheduled ON time for Bin Indicator to scheduler (%d00).", START_BIN_SCHEDULE)
    sched.schedule(next_schedule_time(STOP_BIN_SCHEDULE), sched.binIndicator.hide_bin_indicator, sched)
    logger.info("Added scheduled OFF time for Bin Indicator to scheduler (%d00).", STOP_BIN_SCHEDULE)

    # set default bin illumination (off)
    sched.binLED.push_job("defaultOff", 1, lambda led: LEDpatterns.turn_off(led))
    logger.info("Added default OFF display to Bin Indicator LED to scheduler.")

# ---------------- Main ----------------
if __name__ == "__main__":
    # configure logging
    setup_logging()
    logger.info("Application launched.")

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

    # instantiate binIndicatorController
    binIndicator = binIndicatorController()

    # instantiate scheduler class
    sched = Scheduler(status_led, bin_led, binSched, binIndicator)

    # Kick off initial jobs
    chest = Chest()
    set_initial_jobs(sched)

    # button listener
    # Set up event detection for rising / falling edges
    GPIO.add_event_detect(BUTTON_PIN, GPIO.BOTH, bouncetime=10)
    touch_button_handler = button_handler(PIN=BUTTON_PIN,
                                          single_fun=lambda: binIndicator.toggle_bin_display(sched),
                                          double_fun=lambda: show_next_bin(sched),
                                          long_fun=lambda: soft_reset(sched))
    GPIO.add_event_callback(BUTTON_PIN, touch_button_handler.edge_detected)

    try:
        logger.info("Starting scheduler.")
        sched.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt caught, closing application.")
        sched.stop()
        GPIO.cleanup()
