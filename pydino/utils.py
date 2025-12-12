# utils.py
# 1:1 port of utils.ts for a pygame-based Chrome Dino port.

from __future__ import annotations
import random
import time
try:
    from constants import IS_IOS
except ImportError:
    IS_IOS = False


def get_random_num(min_val: int, max_val: int) -> int:
    """Inclusive integer random: [min_val, max_val]."""
    # TS: Math.floor(Math.random() * (max - min + 1)) + min
    return random.randint(min_val, max_val)


def get_time_stamp() -> int:
    """Current timestamp in milliseconds.
    TS: IS_IOS ? Date().getTime() : performance.now()
    """
    if IS_IOS:
        # Wall-clock ms
        return int(time.time() * 1000)
    # High-resolution monotonic ms
    return int(time.perf_counter() * 1000)


# --- Aliases for TS-style imports (camelCase) ---
getRandomNum = get_random_num
getTimeStamp = get_time_stamp