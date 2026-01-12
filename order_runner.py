import json
from pathlib import Path

from models import Program, Step
from serial_comm import run_program


PROGRAM_DIR = Path("programs")


def _load_program(path: Path) -> Program:
    """
    JSON shape:
      { "name": "...", "steps": [ {cmd,x,y,z,f,delay,do0}, ... ] }
    """
    with path.open("r") as f:
        data = json.load(f)

    steps = []
    for s in data.get("steps", []):
        steps.append(
            Step(
                cmd=s.get("cmd"),
                x=s.get("x"),
                y=s.get("y"),
                z=s.get("z"),
                f=s.get("f"),
                delay=s.get("delay", 0.5),
                do0=s.get("do0"),
            )
        )

    return Program(name=data.get("name", "unnamed"), steps=steps)


def run_order(juice_key: str) -> None:
    origin_prog = _load_program(PROGRAM_DIR / "orgin.json")
    common_prog = _load_program(PROGRAM_DIR / "common" / "pick_cup.json")
    juice_prog  = _load_program(PROGRAM_DIR / "juices" / f"{juice_key}.json")

    all_steps = []
    all_steps += origin_prog.steps
    all_steps += common_prog.steps
    all_steps += juice_prog.steps

    full_prog = Program(name=f"order_{juice_key}", steps=all_steps)
    run_program(full_prog)
