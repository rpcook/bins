import sys
import time
import threading

class MockPWM:
    _instances = []
    _lock = threading.Lock()

    def __init__(self, pin, frequency):
        print(f"[MockGPIO] Creating PWM on pin {pin} at {frequency}Hz")
        self.pin = pin
        self.frequency = frequency
        self.duty_cycle = 0
        self.running = False

        # Register this instance
        with MockPWM._lock:
            MockPWM._instances.append(self)

        # Start background thread to show bars
        if not hasattr(MockPWM, "_display_thread"):
            MockPWM._stop_display = False
            MockPWM._display_thread = threading.Thread(target=self._display_loop, daemon=True)
            MockPWM._display_thread.start()

    def start(self, duty_cycle):
        self.duty_cycle = duty_cycle
        self.running = True
        print(f"[MockPWM] Started PWM on pin {self.pin} at {self.frequency}Hz with duty cycle {self.duty_cycle}%")

    def ChangeDutyCycle(self, duty_cycle):
        if not self.running:
            print("[MockPWM] Warning: PWM not started yet")
        self.duty_cycle = duty_cycle
        # print(f"[MockPWM] Changed duty cycle on pin {self.pin} to {self.duty_cycle}%")

    def ChangeFrequency(self, frequency):
        if not self.running:
            print("[MockPWM] Warning: PWM not started yet")
        self.frequency = frequency
        print(f"[MockPWM] Changed frequency on pin {self.pin} to {self.frequency}Hz")

    def stop(self):
        self.running = False
        print(f"[MockPWM] Stopped PWM on pin {self.pin}")

    @classmethod
    def _display_loop(cls):
        """ Continuously updates the console with all PWM bars on one line. """
        while not getattr(cls, "_stop_display", False):
            with cls._lock:
                bars = []
                for pwm in cls._instances:
                    val = pwm.duty_cycle if pwm.running else 0
                    filled = int(val / 5)  # 20 chars wide (0–100%)
                    bar = "#" * filled + "-" * (20 - filled)
                    bars.append(f"Pin {pwm.pin:2d} [{bar}] {val:3.0f}%")
                sys.stdout.write("\r" + " | ".join(bars) + " " * 10)
                sys.stdout.flush()
            time.sleep(0.1)

    @classmethod
    def shutdown_display(cls):
        """ Stop background thread (optional). """
        cls._stop_display = True
        if hasattr(cls, "_display_thread"):
            cls._display_thread.join(timeout=1)

class MockGPIO:
    BOARD = "BOARD"
    BCM = "BCM"
    OUT = "OUT"
    IN = "IN"
    RISING = "RISING"
    FALLING = "FALLING"
    BOTH = "BOTH"
    HIGH = 1
    LOW = 0

    def __init__(self):
        self.mode = None
        self.pins = {}

    def setmode(self, mode):
        self.mode = mode
        print(f"[MockGPIO] Mode set to {mode}")

    def setup(self, pin, mode):
        self.pins[pin] = {"mode": mode, "state": self.LOW}
        print(f"[MockGPIO] Pin {pin} set up as {mode}")

    def output(self, pin, state):
        if pin in self.pins and self.pins[pin]["mode"] == self.OUT:
            self.pins[pin]["state"] = state
            print(f"[MockGPIO] Pin {pin} output set to {state}")
        else:
            print(f"[MockGPIO] Error: Pin {pin} not configured as OUT")

    def input(self, pin):
        state = self.pins.get(pin, {}).get("state", self.LOW)
        print(f"[MockGPIO] Pin {pin} read as {state}")
        return state

    def PWM(self, pin, frequency):
        return MockPWM(pin, frequency)
    
    def add_event_detect(self, pin, edge, bouncetime):
        print(f"[MockGPIO] Add event detect on {pin} edge {edge} with bouncetime {bouncetime}ms")

    def add_event_callback(self, pin, callback):
        print(f"[MockGPIO] Add event callback on {pin} with callback {callback}")

    def cleanup(self):
        self.pins.clear()
        print("[MockGPIO] Cleaned up all pins")
