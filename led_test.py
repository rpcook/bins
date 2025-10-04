import heapq
import threading
import time

class LEDController:
    def __init__(self, update_func):
        self.update_func = update_func  # function to set PWM outputs
        self.jobs = []                  # heap: [(-priority, job_id, fn)]
        self.cancelled = set()          # set of cancelled job_ids
        self.job_id = 0
        self.lock = threading.Lock()
        self.running = True
        self.worker = threading.Thread(target=self._run, daemon=True)
        self.worker.start()

    def add_job(self, priority, fn):
        """Add a new LED job with priority and update function. Returns job_id."""
        with self.lock:
            self.job_id += 1
            job_id = self.job_id
            heapq.heappush(self.jobs, (-priority, job_id, fn))
            return job_id

    def remove_job(self, job_id):
        """Mark a job as cancelled (will be skipped when encountered)."""
        with self.lock:
            self.cancelled.add(job_id)

    def remove_top(self):
        """Convenience: cancel the current top job."""
        with self.lock:
            if self.jobs:
                _, job_id, _ = self.jobs[0]
                self.cancelled.add(job_id)

    def _get_next_job(self):
        """Return the highest priority non-cancelled job, or None."""
        while self.jobs:
            priority, job_id, fn = self.jobs[0]
            if job_id in self.cancelled:
                # discard cancelled jobs
                heapq.heappop(self.jobs)
                self.cancelled.remove(job_id)
                continue
            return fn
        return None

    def _run(self):
        while self.running:
            fn = None
            with self.lock:
                fn = self._get_next_job()

            if fn:
                fn(self.update_func)  # run pattern
            else:
                time.sleep(0.1)       # idle wait

    def stop(self):
        self.running = False
        self.worker.join()

# ---------------------------
# Example LED job functions
# ---------------------------

def solid_green(update_func):
    update_func(0, 100, 0)
    time.sleep(0.5)

def solid_red(update_func):
    update_func(100, 0, 0)
    time.sleep(0.5)

def pulse_green(update_func):
    for i in range(0, 101, 10):
        update_func(0, i, 0)
        time.sleep(0.05)
    for i in range(100, -1, -10):
        update_func(0, i, 0)
        time.sleep(0.05)

# ---------------------------
# Example usage
# ---------------------------

def dummy_update(r, g, b):
    print(f"LED -> R:{r} G:{g} B:{b}")

if __name__ == "__main__":
    led = LEDController(dummy_update)

    # Add jobs
    j1 = led.add_job(1, solid_green)
    time.sleep(1)
    j2 = led.add_job(2, solid_red)  # higher priority overrides
    time.sleep(1)

    # green pulse job
    j3 = led.add_job(4, pulse_green)
    time.sleep(2)

    # Remove red job (falls back to green)
    led.remove_job(j3)
    time.sleep(2)

    # Add green pulse job, then cancel before it shows
    led.remove_job(j2)  # prevent fallback to this
    time.sleep(2)

    led.stop()
