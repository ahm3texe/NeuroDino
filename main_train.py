#!/usr/bin/env python3
"""Trains the network with a genetic algorithm.

Every generation, each network plays the same few games, one per seed, the
way the website plays them (neurodino/episode.py); the games run in parallel.
A network's fitness is its mean score, with every game cut off after
--minutes of game time. Then the next generation is bred (neurodino/genetics.py).

Training starts from a saved network (--start, by default best_brain.pkl: the
best plus mutated copies of it) or from random weights (--start random). The
seeds follow from --seed, so a run can be repeated exactly. Everything goes
to --out: the log, the best network of every generation, and at the end the
network that scores best on separate validation games.

    python main_train.py --generations 40
"""
import argparse
import csv
import os
import pickle
import random
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / "pydino"))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from neurodino.brain import Brain  # noqa: E402
from neurodino.genetics import Genetics  # noqa: E402

FPS = 60
SCORE_PER_PIXEL = 0.025
VALIDATION_SEEDS = 500_000   # validation games use seeds from here on
TRAINING_SEEDS = 1_000_000   # training games: TRAINING_SEEDS * --seed onwards


def _init_worker():
    import pygame
    pygame.init()
    pygame.display.set_mode((600, 150))


def _play(job):
    from neurodino.episode import play
    brains, seed, max_frames = job
    return play(brains, seed, max_frames)


def load_brain(path):
    with open(path, "rb") as f:
        data = pickle.load(f)
    return data[0] if isinstance(data, tuple) else data


def play_games(pool, brains, seeds, max_frames):
    """Scores and whether each brain lasted the whole game: one row per game,
    one column per brain."""
    games = np.array(pool.map(_play, [(brains, seed, max_frames) for seed in seeds]))
    return games[:, :, 0] * SCORE_PER_PIXEL, games[:, :, 1].astype(bool)


def main():
    parser = argparse.ArgumentParser(description="Train NeuroDino with a genetic algorithm.")
    parser.add_argument("--start", default="best_brain.pkl",
                        help="network to start from, or 'random' (default: best_brain.pkl)")
    parser.add_argument("--generations", type=int, default=40)
    parser.add_argument("--population", type=int, default=50)
    parser.add_argument("--games", type=int, default=10, help="games per generation")
    parser.add_argument("--minutes", type=float, default=30, help="game time before a game is cut off")
    parser.add_argument("--mutation", type=float, default=0.05,
                        help="lowest mutation rate; the rate falls to it as scores grow")
    parser.add_argument("--shock", type=float, default=0.08,
                        help="share of mutated weights replaced by a random value instead of nudged")
    parser.add_argument("--validation-games", type=int, default=100)
    parser.add_argument("--validation-minutes", type=float, default=30)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--workers", type=int, default=os.cpu_count())
    parser.add_argument("--out", default="runs/train")
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    max_frames = int(args.minutes * 60 * FPS)

    genetics = Genetics(args.population)
    if args.start == "random":
        genetics.create_random_population(input_size=12, hidden_size=48, output_size=3)
        population = genetics.genomes
    else:
        # The starting network and copies of it mutated at the GA's lowest
        # rate: stronger mutation breaks most copies of a trained network.
        start = load_brain(args.start)
        population = [start.copy()]
        for _ in range(args.population - 1):
            child = start.copy()
            child.mutate(0.05, args.shock)
            population.append(child)

    log_path = out / "training_log.csv"
    with log_path.open("w", newline="") as f:
        csv.writer(f).writerow(["Generation", "Best", "Average", "Median", "Best_Worst_Game",
                                "Full_Games", "Mutation_Rate", "Seconds"])

    record = 0.0
    best_per_generation = []
    with Pool(args.workers, initializer=_init_worker) as pool:
        for generation in range(1, args.generations + 1):
            started = time.time()
            first = TRAINING_SEEDS * args.seed + (generation - 1) * args.games
            scores, lasted = play_games(pool, population, range(first, first + args.games), max_frames)
            fitness = scores.mean(axis=0)
            best = int(np.argmax(fitness))
            record = max(record, float(fitness[best]))
            full = float(lasted.mean())
            rate = max(args.mutation, min(0.25, 0.20 * 0.995 ** generation / (1 + record / 2000)))

            brain = population[best].copy()
            best_per_generation.append((generation, brain))
            with (out / f"generation_{generation:03d}.pkl").open("wb") as f:
                pickle.dump((brain, float(fitness[best])), f)
            seconds = time.time() - started
            with log_path.open("a", newline="") as f:
                csv.writer(f).writerow([generation, round(float(fitness[best])), round(float(fitness.mean())),
                                        round(float(np.median(fitness))), round(float(scores[:, best].min())),
                                        round(full, 3), round(rate, 4), round(seconds, 1)])
            print(f"Generation {generation}: best {fitness[best]:,.0f} (worst game {scores[:, best].min():,.0f}), "
                  f"average {fitness.mean():,.0f}, full games {full:.0%}, {seconds:.0f} s", flush=True)

            population = genetics.evolve_population(list(zip(population, fitness)),
                                                    generation=generation, best_score=record,
                                                    min_rate=args.mutation, shock_rate=args.shock)

        # Pick the network that does best on games none of them trained on.
        if args.validation_games:
            candidates = [(0, load_brain(args.start))] if args.start != "random" else []
            candidates += best_per_generation
            seeds = range(VALIDATION_SEEDS, VALIDATION_SEEDS + args.validation_games)
            scores, lasted = play_games(pool, [b for _, b in candidates], seeds,
                                        int(args.validation_minutes * 60 * FPS))
            fitness = scores.mean(axis=0)
            full = lasted.mean(axis=0)
            with (out / "validation.csv").open("w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Generation", "Average", "Full_Games"])
                for (generation, _), value, share in zip(candidates, fitness, full):
                    writer.writerow([generation, round(float(value)), round(float(share), 3)])
            best = int(np.argmax(fitness))
            generation, brain = candidates[best]
            with (out / "best_brain.pkl").open("wb") as f:
                pickle.dump((brain, int(round(float(fitness[best])))), f)
            print(f"Validation: generation {generation} is best, average {fitness[best]:,.0f}, "
                  f"full games {full[best]:.0%} (generation 0 is the starting network)", flush=True)


if __name__ == "__main__":
    main()
