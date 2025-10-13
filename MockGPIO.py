import sys
import time
import threading

class MockPWM:
    # _instances = []
    # _lock = threading.Lock()

    def __init__(self, pin, frequency, display=None):
        print(f"[MockGPIO] Creating PWM on pin {pin} at {frequency}Hz")
        self.pin = pin
        self.frequency = frequency
        self.duty_cycle = 0
        self.display = display
        # self.running = False

        # # Register this instance
        # with MockPWM._lock:
        #     MockPWM._instances.append(self)

        # # Start background thread to show bars
        # if not hasattr(MockPWM, "_display_thread"):
        #     MockPWM._stop_display = False
        #     MockPWM._display_thread = threading.Thread(target=self._display_loop, daemon=True)
        #     MockPWM._display_thread.start()

    def start(self, duty_cycle):
        self.duty_cycle = duty_cycle
        self.running = True
        print(f"[MockPWM] Started PWM on pin {self.pin} at {self.frequency}Hz with duty cycle {self.duty_cycle}%")

    def ChangeDutyCycle(self, duty_cycle):
        if not self.running:
            print("[MockPWM] Warning: PWM not started yet")
        self.duty_cycle = duty_cycle
        self._update_display()

    def ChangeFrequency(self, frequency):
        if not self.running:
            print("[MockPWM] Warning: PWM not started yet")
        self.frequency = frequency
        print(f"[MockPWM] Changed frequency on pin {self.pin} to {self.frequency}Hz")

    def stop(self):
        self.running = False
        print(f"[MockPWM] Stopped PWM on pin {self.pin}")

    def _update_display(self):
        """Tell the shared display about any change."""
        if not self.display:
            return

        # Get current LED RGB triple from display
        gpio_pin_to_led_index = {21: 0, 18: 0, 11: 0,
                                 10: 1, 9:  1, 17: 1}
        
        current = list(self.display.rgb_values[gpio_pin_to_led_index[self.pin]])
        gpio_pin_to_led_colour_index = {21: 0, 18: 1, 11: 2,
                                        10: 0, 9:  1, 17: 2}
        current[gpio_pin_to_led_colour_index[self.pin]] = self.duty_cycle
        self.display.update_led(gpio_pin_to_led_index[self.pin], tuple(current))
   
    # --- Helper for colours ---
    # @staticmethod
    # def _get_colour_code(pin):
        # """Return an ANSI colour based on pin number."""
        # colours = {21: "\033[31m", 18: "\033[32m", 11: "\033[34m",
        #            10: "\033[31m", 9: "\033[32m", 17: "\033[34m"}
        # return colours.get(pin, "\033[90m")  # Grey default

    # @classmethod
    # def _display_loop(cls):
    #     """ Continuously updates the console with all PWM bars on one line. """
    #     while not getattr(cls, "_stop_display", False):
    #         with cls._lock:
    #             bars = []
    #             for pwm in cls._instances:
    #                 val = pwm.duty_cycle if pwm.running else 0
    #                 filled = int(val / 10)  # 20 chars = 0–100%
    #                 bar = "#" * filled + "-" * (10 - filled)

    #                 color = cls._get_colour_code(pwm.pin)
    #                 reset = "\033[0m"
    #                 bars.append(f"{color}Pin {pwm.pin:>2} [{bar}] {val:3.0f}%{reset}")

    #             sys.stdout.write("\r" + " | ".join(bars) + " " * 10)
    #             sys.stdout.flush()
    #         time.sleep(0.1)

    # @classmethod
    # def shutdown_display(cls):
        # """ Stop background thread (optional). """
        # cls._stop_display = True
        # if hasattr(cls, "_display_thread"):
        #     cls._display_thread.join(timeout=1)
        # # Reset terminal colours and move to new line
        # sys.stdout.write("\033[0m\n")
        # sys.stdout.flush()

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
        self.display = LEDBarDisplay(refresh_rate=0.05)

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
        return MockPWM(pin, frequency, self.display)
    
    def add_event_detect(self, pin, edge, bouncetime):
        print(f"[MockGPIO] Add event detect on {pin} edge {edge} with bouncetime {bouncetime}ms")

    def add_event_callback(self, pin, callback):
        print(f"[MockGPIO] Add event callback on {pin} with callback {callback}")

    def cleanup(self):
        self.pins.clear()
        print("[MockGPIO] Cleaned up all pins")

class LEDBarDisplay:
    def __init__(self, num_leds=2, refresh_rate=0.2):
        self.num_leds = num_leds
        self.rgb_values = [[0, 0, 0] for _ in range(num_leds)]
        self.refresh_rate = refresh_rate
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run_display, daemon=True)
        self._thread.start()
        self._printed_lines = 0

    def update_led(self, led_index, rgb_tuple):
        """Update the displayed duty cycle for one LED."""
        self.rgb_values[led_index] = rgb_tuple

    def _run_display(self):
        """Continuously refresh the bar graph display."""
        num_lines = self.num_leds + 1  # +1 for a header or spacing line

        # Move cursor to bottom and reserve lines for display
        sys.stdout.write("\n" * num_lines)
        sys.stdout.flush()
        while not self._stop.is_set():
            # Save cursor position
            # sys.stdout.write(f"\033[{num_lines}F")  # Move cursor up num_lines
            sys.stdout.write("\033[?25l")           # Hide cursor

            # Draw header
            sys.stdout.write("\033[2K")  # clear line
            sys.stdout.write("= LED STATUS =\n")

            for i, (r, g, b) in enumerate(self.rgb_values):
                def colour_bar(value, colour_code):
                    bar = "█" * int(value / 5)
                    return f"\033[{colour_code}m{bar:<20}\033[0m"

                bar_r = colour_bar(r, 31)  # Red
                bar_g = colour_bar(g, 32)  # Green
                bar_b = colour_bar(b, 34)  # Blue

                sys.stdout.write("\033[2K")  # clear line
                sys.stdout.write(f"LED{i+1} | R:{bar_r} G:{bar_g} B:{bar_b}\n")

            sys.stdout.flush()
            sys.stdout.write("\033[?25h")           # show cursor again
            sys.stdout.write(f"\033[{num_lines}F")  # Move cursor up num_lines
            time.sleep(self.refresh_rate)

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join()
        print("\033[?25h")  # ensure cursor is visible
