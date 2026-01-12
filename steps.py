"""
Step classes for robot program
"""

class Step:
    """Base class for all step types."""
    
    def __init__(self):
        self.step_type = "base"
    
    def to_dict(self):
        """Convert step to dictionary for JSON serialization."""
        return {"type": self.step_type}
    
    def to_gcode(self):
        """Convert step to G-code command."""
        return ""
    
    def __str__(self):
        """String representation."""
        return f"Step({self.step_type})"


class MoveStep(Step):
    """Movement step with X, Y, Z coordinates."""
    
    def __init__(self, x=0.0, y=0.0, z=0.0, feedrate=200):
        """
        Initialize move step.
        
        Args:
            x: X coordinate in mm
            y: Y coordinate in mm
            z: Z coordinate in mm
            feedrate: Movement speed (1-500)
        """
        super().__init__()
        self.step_type = "move"
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
        self.feedrate = int(feedrate)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "type": "move",
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "feedrate": self.feedrate
        }
    
    def to_gcode(self):
        """Convert to G-code with protocol wrapper."""
        return f"0x550xAA G01 X{self.x:.1f} Y{self.y:.1f} Z{self.z:.1f} F{self.feedrate} P0 0xAA0x55"
    
    def __str__(self):
        """String representation."""
        return f"Move(X:{self.x:.1f}, Y:{self.y:.1f}, Z:{self.z:.1f}, F:{self.feedrate})"


class WaitStep(Step):
    """Wait/delay step."""
    
    def __init__(self, duration=1.0):
        """
        Initialize wait step.
        
        Args:
            duration: Wait time in seconds
        """
        super().__init__()
        self.step_type = "wait"
        self.duration = float(duration)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "type": "wait",
            "duration": self.duration
        }
    
    def to_gcode(self):
        """Convert to G-code (G04 dwell command)."""
        return f"G04 P{int(self.duration * 1000)}"  # P in milliseconds
    
    def __str__(self):
        """String representation."""
        return f"Wait({self.duration}s)"


class PumpStep(Step):
    """Air pump control step."""
    
    def __init__(self, state="on"):
        """
        Initialize pump step.
        
        Args:
            state: "on" or "off"
        """
        super().__init__()
        self.step_type = "pump"
        self.state = state.lower()
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "type": "pump",
            "state": self.state
        }
    
    def to_gcode(self):
        """Convert to G-code."""
        s_value = 1 if self.state == "on" else 0
        return f"0x550xAA G06 D6 S{s_value} P0 0xAA0x55"
    
    def __str__(self):
        """String representation."""
        return f"Pump({self.state})"


class GripperStep(Step):
    """Hand gripper control step."""
    
    def __init__(self, state="open"):
        """
        Initialize gripper step.
        
        Args:
            state: "open" or "close"
        """
        super().__init__()
        self.step_type = "gripper"
        self.state = state.lower()
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "type": "gripper",
            "state": self.state
        }
    
    def to_gcode(self):
        """Convert to G-code."""
        s_value = 1 if self.state == "open" else 0
        return f"0x550xAA G06 D7 S{s_value} P1 0xAA0x55"
    
    def __str__(self):
        """String representation."""
        return f"Gripper({self.state})"


# Factory function to create steps from dictionary
def step_from_dict(data):
    """
    Create step object from dictionary.
    
    Args:
        data: Dictionary with step data
    
    Returns:
        Step object
    """
    step_type = data.get("type", "move")
    
    if step_type == "move":
        return MoveStep(
            x=data.get("x", 0),
            y=data.get("y", 0),
            z=data.get("z", 0),
            feedrate=data.get("feedrate", 200)
        )
    elif step_type == "wait":
        return WaitStep(duration=data.get("duration", 1.0))
    elif step_type == "pump":
        return PumpStep(state=data.get("state", "on"))
    elif step_type == "gripper":
        return GripperStep(state=data.get("state", "open"))
    else:
        return Step()
