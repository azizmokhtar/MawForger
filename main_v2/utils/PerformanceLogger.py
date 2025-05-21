import time
import os
import random
from functools import wraps
from threading import Lock
from typing import Any, Callable

class FastLogger:
    def __init__(self, log_file: str = "perf.log", buffer_size: int = 1000, enabled: bool = True):
        self.enabled = enabled
        self.buffer_size = buffer_size
        self.buffer = []
        self.lock = Lock()
        self.log_file = log_file

        # Ensure path exists
        os.makedirs(os.path.dirname(log_file) or '.', exist_ok=True)

    def _write_buffer(self):
        if not self.buffer:
            return
        try:
            with open(self.log_file, 'a') as f:
                f.write('\n'.join(self.buffer) + '\n')
            self.buffer.clear()
        except Exception as e:
            print(f"[FastLogger] Write error: {e}")

    def log(self, line: str):
        if not self.enabled:
            return
        with self.lock:
            self.buffer.append(line)
            if len(self.buffer) >= self.buffer_size:
                self._write_buffer()

    def measure(self, func_name: str = None, sample_rate: float = 1.0):
        def decorator(func: Callable) -> Callable:
            name = func_name or func.__name__

            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled or (sample_rate < 1.0 and random.random() > sample_rate):
                    return func(*args, **kwargs)

                start = time.monotonic()
                result = func(*args, **kwargs)
                duration = time.monotonic() - start
                self.log(f"{name},{duration:.9f},{start:.9f}")
                return result
            return wrapper
        return decorator

    def measure_async(self, func_name: str = None, sample_rate: float = 1.0):
        def decorator(func: Callable) -> Callable:
            name = func_name or func.__name__

            @wraps(func)
            async def wrapper(*args, **kwargs):
                if not self.enabled or (sample_rate < 1.0 and random.random() > sample_rate):
                    return await func(*args, **kwargs)

                start = time.monotonic()
                result = await func(*args, **kwargs)
                duration = time.monotonic() - start
                self.log(f"{name},{duration:.9f},{start:.9f}")
                return result
            return wrapper
        return decorator

    def shutdown(self):
        """Call this at exit to flush remaining logs"""
        with self.lock:
            self._write_buffer()


# EXAMPLE USE CASE

##from fast_logger import FastLogger
##
##perf_logger = FastLogger(log_file="logs/perf.csv", buffer_size=5000, enabled=True)
##
##@perf_logger.measure("place_order", sample_rate=0.1)
##def place_order(symbol, amount):
##    # Simulate fast logic
##    return True
##
##@perf_logger.measure_async("fetch_price", sample_rate=0.2)
##async def fetch_price(pair):
##    # Simulate async call
##    return 100.0