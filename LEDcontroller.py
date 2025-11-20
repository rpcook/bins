# import heapq
import threading
import time

class LEDcontroller:
    def __init__(self, pwm_channels, inverted=False, update_rate=0.05):
        """
        pwm_channels: tuple/list of 3 PWM objects (R, G, B)
        inverted: bool or tuple/list of bools (one per channel)
        update_rate: seconds between pattern updates
        """
        if not isinstance(pwm_channels, (tuple, list)) or len(pwm_channels) != 3:
            raise ValueError("pwm_channels must be a tuple/list of 3 PWM objects (R, G, B)")

        self.pwm_channels = pwm_channels

        if isinstance(inverted, (tuple, list)):
            if len(inverted) != 3:
                raise ValueError("inverted tuple must have 3 elements (for R,G,B)")
            self.inverted = inverted
        else:
            self.inverted = (inverted, inverted, inverted)
        
        self.update_rate = update_rate
        self.lock = threading.Lock()
        self.jobs = {}  # {job_id: (priority, generator)}
        self.active = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    # -----------------------------
    # LED hardware interface
    # -----------------------------
    def _apply_rgb(self, r, g, b):
        """Directly set RGB LED brightness values (0–100)."""
        channels = [r, g, b]
        for i, pwm in enumerate(self.pwm_channels):
            duty = 100 - channels[i] if self.inverted[i] else channels[i]
            pwm.ChangeDutyCycle(duty)

    # -----------------------------
    # Job control
    # -----------------------------
    def push_job(self, job_id, priority, generator_func):
        """
        Add or replace a job.
        generator_func must be a generator function that yields repeatedly.
        """
        with self.lock:
            self.jobs[job_id] = (priority, generator_func(self))
            # sort jobs implicitly by priority when choosing active job

    def remove_job(self, job_id):
        """Remove a job by its ID."""
        with self.lock:
            if job_id in self.jobs:
                del self.jobs[job_id]

    def clear_jobs(self):
        with self.lock:
            self.jobs.clear()

    # -----------------------------
    # Main loop
    # -----------------------------
    def _run(self):
        """Main LED control loop."""
        while self.active:
            with self.lock:
                if not self.jobs:
                    job = None
                else:
                    # get highest-priority job
                    job = max(self.jobs.items(), key=lambda kv: kv[1][0])[1][1]

            if job:
                try:
                    next(job)  # advance one step
                except StopIteration:
                    # finished pattern; remove automatically
                    with self.lock:
                        for jid, (_, gen) in list(self.jobs.items()):
                            if gen is job:
                                del self.jobs[jid]
                                break
                except Exception as e:
                    print(f"[LEDController] Job error: {e}")
            else:
                time.sleep(self.update_rate)
        print("LED controller stopped")

    def stop(self):
        self.active = False
        self.thread.join()

# ---------------------------
# LED job functions
# ---------------------------

def solid_red(led):
    """Static red light (runs until replaced or removed)."""
    while True:
        led._apply_rgb(100, 0, 0)
        yield  # yield control back to controller

def pulse_green(led):
    """Smoothly pulse green."""
    brightness = 0
    direction = 5
    while True:
        led._apply_rgb(0, brightness, 0)
        brightness += direction
        if brightness >= 100 or brightness <= 0:
            direction *= -1
        time.sleep(0.02)
        yield  # yield every small step

def flash_blue(led):
    """Quick flash sequence."""
    for _ in range(4):
        led._apply_rgb(0, 0, 100)
        time.sleep(0.1)
        yield
        led._apply_rgb(0, 0, 0)
        time.sleep(0.1)
        yield
    # stop automatically after a few flashes

if __name__ == "__main__":
# ---- GPIO library with mock for PC development ----
    try:
        import RPi.GPIO as GPIO # type: ignore
    except ImportError:
        from MockGPIO import MockGPIO
        GPIO = MockGPIO()
    GPIO.setmode(GPIO.BCM)

    STATUS_RED = 21
    STATUS_GREEN_BAR = 18
    STATUS_BLUE = 11
    BIN_RED = 10
    BIN_GREEN = 9
    BIN_BLUE = 17

    pins = (STATUS_RED, STATUS_GREEN_BAR, STATUS_BLUE)
    pwms = []
    for p in pins:
        GPIO.setup(p, GPIO.OUT)
        pwm = GPIO.PWM(p, 200)
        pwm.start(0)
        pwms.append(pwm)

    status_led = LEDcontroller(tuple(pwms), [False, True, False])

    pins = (BIN_RED, BIN_GREEN, BIN_BLUE)
    pwms = []
    for p in pins:
        GPIO.setup(p, GPIO.OUT)
        pwm = GPIO.PWM(p, 200)
        pwm.start(0)
        pwms.append(pwm)

    bin_led = LEDcontroller(tuple(pwms))

    # --- Control sequence ---
    status_led.push_job("error", 2, solid_red)
    time.sleep(2)
    status_led.remove_job("error")
    status_led.push_job("heartbeat", 1, pulse_green)
    time.sleep(2)
    status_led.push_job("alert", 10, flash_blue)  # temporarily override
    time.sleep(2)
    status_led.remove_job("alert")  # goes back to heartbeat
    print("\033[2B") # move cursor to bottom
