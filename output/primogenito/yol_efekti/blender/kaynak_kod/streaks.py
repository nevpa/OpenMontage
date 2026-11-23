"""Parameters of the green road-streak effect (same seed/values as the rendered clip)."""
import random
import numpy as np

W, H, FPS = 1080, 1920, 30
n = 170
KEY = [(0, 1300), (15, 1420), (30, 1490), (45, 1555), (60, 1594), (75, 1615), (120, 1708), (135, 1740), (150, 1723), (169, 1780)]
GROUND = np.interp(np.arange(n), [k for k, _ in KEY], [v for _, v in KEY])
LIGHT, MINT, WHITE = (0, 200, 110), (110, 255, 180), (235, 255, 245)

rng = random.Random(21)
STREAKS = []
for _ in range(46):
    v = rng.random() ** 0.8
    STREAKS.append(dict(v=v, L=rng.uniform(260, 900) * (0.55 + v), th=2 + 11 * v * rng.uniform(0.6, 1.0),
                        speed=(38 + 85 * v) * rng.uniform(0.85, 1.15), ph=rng.uniform(0, 4000),
                        col=rng.choice([LIGHT, LIGHT, MINT, MINT, WHITE])))
