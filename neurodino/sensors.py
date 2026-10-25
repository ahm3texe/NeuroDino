# neurodino/sensors.py
"""The network's 12 inputs, read from a running game.

Shared by the trainer (episode.py), the v1 training runner (neuro_runner.py)
and the watcher (watch_model.py). The website computes the same values in
web/src/watcher.ts.
"""
import numpy as np

MAX_OBSTACLE_WIDTH = 75   # widths are divided by this
MAX_TTI_FRAMES = 50.0     # obstacles further away than this many frames read as 0
DUCK_THRESHOLD_Y = 75     # Act is 1 for obstacles above this y: only the highest bird
GAP_FRAMES = 15.0         # gaps longer than this many frames read as 0


def get_inputs(runner, dino) -> np.ndarray:
    """Obj1 Dist/Act/W, Obj2 Dist/Act/W, Speed, Gap, DinoY, DinoVel, Air, Duck.

    Obstacles are the nearest two ahead of the dino's left edge; distances are
    turned into frames to impact at the current speed, so 1 is about to hit.
    """
    speed = runner.current_speed / runner.config.maxSpeed

    dino_y = 0.0
    dino_velocity = 0.0
    if dino.jumping:
        dino_y = min(1.0, max(0.0, (dino.groundYPos - dino.yPos) / dino.config.maxJumpHeight))
        dino_velocity = max(-1.0, min(1.0, dino.jumpVelocity / 10.0))
    airborne = 1.0 if dino.jumping else 0.0
    ducking = 1.0 if dino.ducking else 0.0

    obs1_dist = obs1_action = obs1_w = 0.0
    obs2_dist = obs2_action = obs2_w = 0.0
    gap = 0.0
    if runner.horizon and runner.horizon.obstacles:
        ahead = sorted((o for o in runner.horizon.obstacles if o.xPos > dino.xPos),
                       key=lambda o: o.xPos)
        if ahead:
            o1 = ahead[0]
            tti1 = (o1.xPos - dino.xPos) / max(1.0, runner.current_speed)
            obs1_dist = 1.0 - min(1.0, tti1 / MAX_TTI_FRAMES)
            obs1_action = 1.0 if o1.yPos < DUCK_THRESHOLD_Y else 0.0
            obs1_w = min(1.0, o1.width / MAX_OBSTACLE_WIDTH)
            if len(ahead) > 1:
                o2 = ahead[1]
                tti2 = (o2.xPos - dino.xPos) / max(1.0, runner.current_speed)
                obs2_dist = 1.0 - min(1.0, tti2 / MAX_TTI_FRAMES)
                obs2_action = 1.0 if o2.yPos < DUCK_THRESHOLD_Y else 0.0
                obs2_w = min(1.0, o2.width / MAX_OBSTACLE_WIDTH)
                time_gap = (o2.xPos - (o1.xPos + o1.width)) / max(1.0, runner.current_speed)
                gap = 1.0 - min(1.0, time_gap / GAP_FRAMES)

    return np.array([
        obs1_dist, obs1_action, obs1_w,
        obs2_dist, obs2_action, obs2_w,
        speed, gap,
        dino_y, dino_velocity,
        airborne, ducking,
    ])
