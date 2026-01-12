# models.py
#
# Data models: Step (single move) and Program (sequence of steps).

import json
from typing import Optional, List
from dataclasses import dataclass, field, asdict


@dataclass
class Step:
    """
    Represents a single robot step.
    - cmd: G00 (rapid) or G01 (linear)
    - x, y, z: coordinates in mm (None = don't move that axis)
    - f: feedrate in mm/min
    - delay: seconds to wait after this step
    - do0: 4th axis angle (gripper servo, 0-180 degrees)
    """
    cmd: str = "G01"
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    f: float = 20.0
    delay: float = 0.5
    do0: Optional[float] = None

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None or k in ("x", "y", "z", "do0")}


@dataclass
class Program:
    """
    A named sequence of Steps.
    Can be saved/loaded as JSON.
    """
    name: str
    steps: List[Step] = field(default_factory=list)

    def to_dict(self):
        return {
            "name": self.name,
            "steps": [s.to_dict() for s in self.steps],
        }

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        prog = cls(name=data.get("name", "unnamed"))
        for step_dict in data.get("steps", []):
            prog.steps.append(Step(**step_dict))
        return prog
