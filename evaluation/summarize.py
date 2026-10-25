#!/usr/bin/env python3
"""Summarizes evaluate.mjs output: how many games ended before top speed, how
many lasted 30 minutes, 2 and 4 hours, and how often the dino crashed at top
speed.

    python evaluation/summarize.py evaluation/data/*.jsonl
"""
import json
import sys

FRAMES_PER_HOUR = 60 * 60 * 60


def summarize(path):
    games = [json.loads(line) for line in open(path)]
    longest = max(g["frames"] for g in games)
    early = sum(g["died"] and g["topSpeedFrame"] < 0 for g in games)
    late = sum(g["died"] and g["topSpeedFrame"] >= 0 for g in games)
    top_hours = sum(g["frames"] - g["topSpeedFrame"] for g in games
                    if g["topSpeedFrame"] >= 0) / FRAMES_PER_HOUR
    lasted = []
    for minutes in (30, 120, 240):
        frames = minutes * 60 * 60
        if frames <= longest:
            n = sum(not g["died"] or g["frames"] >= frames for g in games)
            lasted.append(f"{minutes} min: {n}")
    ducks = sum(g["actions"][1] for g in games)
    rate = f"{late / top_hours:.3f}/h" if top_hours else "-"
    print(f"{path}: {len(games)} games; ended before top speed {early}; "
          f"lasted {', '.join(lasted)}; crashes at top speed {late} in {top_hours:.0f} h ({rate}); "
          f"frames ducking {ducks}")


for path in sys.argv[1:]:
    summarize(path)
