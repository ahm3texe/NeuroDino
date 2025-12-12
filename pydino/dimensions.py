# dimensions.py
# 1:1 port of dimensions.ts (Chrome Dino)
from dataclasses import dataclass

@dataclass
class Dimensions:
    width: int
    height: int