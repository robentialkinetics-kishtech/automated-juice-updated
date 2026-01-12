# config.py
#
# Configuration for ZKBot serial communication.

from pathlib import Path

# Serial port settings - Use COM3 (your robot port)
PORT = "COM3"
BAUD = 9600
BYTESIZE = 8
PARITY = "N"
STOPBITS = 1
TIMEOUT = 2

# Directories
BASE_DIR = Path(__file__).parent
PROGRAMS_DIR = BASE_DIR / "programs"
IMAGES_DIR = BASE_DIR / "images"
# ========== NEW: Speed Override (Upgrade #4) ==========
# Global speed override percentage (10-200%)
# Default: 50% for safe startup during teaching
SPEED_OVERRIDE_PERCENT = 50.0
# Add at the end of config.py

# ========== Order Queue Configuration ==========
# Available juice flavors (maps to program files)
JUICE_FLAVORS = {
    "Orange": "orange.json",
    "Mango": "mango.json",
    "Apple": "apple.json",
    "Mixed": "mixed.json",
    "Custom": None  # Uses current loaded program
}

# Maximum quantity per order
MAX_ORDER_QUANTITY = 10
# ========== Workspace Limits ==========
# ========== Workspace Limits ==========
# Robot workspace limits in millimeters
# Based on ZKBot 3-axis specifications
WORKSPACE_LIMITS = {
    "X": {"min": -400, "max": 400},   # Chassis rotation range
    "Y": {"min": -400, "max": 400},   # Big arm range
    "Z": {"min": -300, "max": 300}    # Forearm range
}

# Home position (origin)
HOME_POSITION = {"X": 0, "Y": 0, "Z": 0}


# ========== Movement Parameters ==========
# Maximum feedrate (speed) for robot movements
# For ZKBot: F parameter range is 1-500
MAX_FEEDRATE = 500  # Maximum speed in mm/min

# Default feedrate for movements
DEFAULT_FEEDRATE = 200  # Medium speed

# Minimum feedrate
MIN_FEEDRATE = 1

