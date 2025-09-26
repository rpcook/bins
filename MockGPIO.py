class MockPWM:
    def __init__(self, pin, frequency):
        self.pin = pin
        self.frequency = frequency
        self.duty_cycle = 0
        self.running = False

    def start(self, duty_cycle):
        self.duty_cycle = duty_cycle
        self.running = True
        print(f"[MockPWM] Started PWM on pin {self.pin} at {self.frequency}Hz with duty cycle {self.duty_cycle}%")

    def ChangeDutyCycle(self, duty_cycle):
        if not self.running:
            print("[MockPWM] Warning: PWM not started yet")
        self.duty_cycle = duty_cycle
        print(f"[MockPWM] Changed duty cycle on pin {self.pin} to {self.duty_cycle}%")

    def ChangeFrequency(self, frequency):
        if not self.running:
            print("[MockPWM] Warning: PWM not started yet")
        self.frequency = frequency
        print(f"[MockPWM] Changed frequency on pin {self.pin} to {self.frequency}Hz")

    def stop(self):
        self.running = False
        print(f"[MockPWM] Stopped PWM on pin {self.pin}")


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
        print(f"[MockGPIO] Creating PWM on pin {pin} at {frequency}Hz")
        return MockPWM(pin, frequency)
    
    def add_event_detect(self, pin, edge, bouncetime):
        print(f"[MockGPIO] Add event detect on {pin} edge {edge} with bouncetime {bouncetime}ms")

    def add_event_callback(self, pin, callback):
        print(f"[MockGPIO] Add event callback on {pin} with callback {callback}")

    def cleanup(self):
        self.pins.clear()
        print("[MockGPIO] Cleaned up all pins")
