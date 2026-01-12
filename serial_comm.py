# serial_comm.py
#
# Serial communication layer: open port, send commands, run programs.

import time
from typing import Optional, List
import serial
import serial.tools.list_ports

from config import PORT, BAUD, BYTESIZE, PARITY, STOPBITS, TIMEOUT
from models import Step, Program


def list_available_ports() -> List[str]:
    """List all available COM ports."""
    ports = []
    try:
        for port_info in serial.tools.list_ports.comports():
            ports.append(port_info.device)
    except Exception as e:
        print(f"Error scanning ports: {e}")
    return ports


def open_port(port: str = None) -> serial.Serial:
    """Open and return the serial port. COM3 only - no fallback."""
    try:
        if port is None:
            port = PORT
        
        print(f"Attempting to open {port}...")
        
        ser = serial.Serial(
            port=port,
            baudrate=BAUD,
            bytesize=BYTESIZE,
            parity=PARITY,
            stopbits=STOPBITS,
            timeout=TIMEOUT,
        )
        print(f"✓ Port {port} opened successfully")
        return ser
    
    except PermissionError as e:
        print(f"✗ PermissionError on {port}: Port may be in use")
        print(f"  Close Arduino IDE, Serial Monitor, or other apps using {port}")
        raise serial.SerialException(
            f"Cannot access {port} - Port in use or access denied.\n"
            f"Close other applications and retry.\n"
            f"Error: {str(e)}"
        )
    
    except FileNotFoundError:
        available = list_available_ports()
        print(f"✗ Port {port} not found")
        print(f"Available ports: {available if available else 'None detected'}")
        raise serial.SerialException(
            f"Port {port} not found.\n"
            f"Available ports: {available if available else 'None'}\n"
            f"Check USB connection and Device Manager."
        )
    
    except serial.SerialException as e:
        print(f"✗ Serial error on {port}: {e}")
        raise


def send_command(ser: serial.Serial, cmd_str: str) -> bytes:
    """Send a G-code command and return the reply."""
    if not ser.is_open:
        raise RuntimeError("Serial port not open")

    data = cmd_str.encode("utf-8")
    written = ser.write(data)
    print(f"Sent: {cmd_str} | bytes: {written}")

    time.sleep(0.5)  # controller processing time
    reply = ser.read(100)
    print(f"Reply: {reply}")
    return reply


def build_move(step: Step, speed_override: float = 1.0) -> Optional[str]:
    """
    Build a G00/G01 XYZ move frame with speed override applied.
    Format: 0x550xAA G01 X... Y... Z... F... 0xAA0x55
    
    Args:
        step: Step object with movement parameters
        speed_override: Speed multiplier (0.1 to 2.0), default 1.0 = 100%
    """
    if step.x is None and step.y is None and step.z is None:
        return None

    cmd = step.cmd if step.cmd in ("G00", "G01") else "G01"
    parts = [cmd]

    if step.x is not None:
        parts.append(f"X{step.x}")
    if step.y is not None:
        parts.append(f"Y{step.y}")
    if step.z is not None:
        parts.append(f"Z{step.z}")

    # Apply speed override to feedrate (integer, 1-500 mm/min)
    effective_speed = int(step.f * speed_override)
    effective_speed = max(1, min(500, effective_speed))  # Clamp to valid range
    parts.append(f"F{effective_speed}")  # No decimal

    gcode = " ".join(parts)
    frame = f"0x550xAA {gcode} 0xAA0x55"
    print(f"FRAME: {frame} (Override: {speed_override*100:.0f}%)")
    return frame


def build_do0(step: Step) -> Optional[str]:
    """
    Build a G06 command for DO-0 (4th axis gripper).
    Format: 0x550xAA G06 D7 S1 A<angle> 0xAA0x55
    """
    if step.do0 is None:
        return None

    angle = int(step.do0)
    angle = max(0, min(180, angle))  # Clamp to servo range 0-180
    gcode = f"G06 D7 S1 A{angle}"
    frame = f"0x550xAA {gcode} 0xAA0x55"
    return frame


def run_program(prog: Program, speed_override: float = 1.0) -> None:
    """
    Run all steps in a Program sequentially.
    Blocking call - wrap in thread for GUI use.
    
    Args:
        prog: Program to execute
        speed_override: Speed multiplier (0.1 to 2.0), default 1.0 = 100%
    """
    ser = open_port()
    try:
        for i, step in enumerate(prog.steps, start=1):
            print(f"--- Step {i} ---")

            # DO0 (gripper) first if set
            do_cmd = build_do0(step)
            if do_cmd:
                send_command(ser, do_cmd)

            # XYZ move with speed override
            move_cmd = build_move(step, speed_override)
            if move_cmd:
                send_command(ser, move_cmd)

            # delay before next step
            time.sleep(step.delay)
    finally:
        ser.close()
        print("Serial port closed.")


def query_position() -> dict:
    """
    Query current robot position (SAFE VERSION).
    
    Returns:
        dict: {'x': 0.0, 'y': 0.0, 'z': 0.0} - safe defaults
    """
    try:
        import serial
        
        ser = serial.Serial(
            port=PORT,
            baudrate=BAUD,
            timeout=TIMEOUT
        )
        
        # MANUAL mode position query: 0xff 0xfe 0x0c 0xfd 0xfc
        cmd = bytes([0xff, 0xfe, 0x0c, 0xfd, 0xfc])
        ser.write(cmd)
        
        # VERY short wait (don't hang)
        ser.timeout = 0.1
        response = ser.read(32).decode('utf-8', errors='ignore')  # Max 32 chars
        
        ser.close()
        
        # Parse "X,Y,Z,ok"
        if ',' in response and 'ok' in response.lower():
            parts = [p.strip() for p in response.split(',')]
            if len(parts) >= 3:
                try:
                    x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
                    return {'x': x, 'y': y, 'z': z}
                except:
                    pass
        
        return {'x': 0.0, 'y': 0.0, 'z': 0.0}
        
    except:
        # NEVER crash or spam errors
        return {'x': 0.0, 'y': 0.0, 'z': 0.0}



def check_emergency_stop(ser: serial.Serial = None) -> dict:
    """
    Check if emergency stop button is pressed using G14 protocol.
    Command: 0x550xAA G14 0xAA0x55
    
    Returns: {
        'is_pressed': bool,    # True if E-stop active
        'status': str,         # 'normal', 'e_stop_active', or error message
        'raw_response': str    # Raw response from robot
    }
    
    Protocol reference [file:14]:
    - Sends: 0x550xAA G14 0xAA0x55
    - Response if pressed: "error\\r\\n"
    - Response if normal: "ok\\r\\n"
    """
    close_after = False
    
    try:
        # Open port if not provided
        if ser is None:
            ser = open_port()
            close_after = True
        
        if not ser.is_open:
            return {
                'is_pressed': None,
                'status': 'Port closed',
                'raw_response': ''
            }
        
        # Send G14 emergency stop query command
        cmd = "0x550xAA G14 0xAA0x55"
        data = cmd.encode("utf-8")
        ser.write(data)
        
        # Wait for response
        time.sleep(0.3)
        
        # Read response
        response = ser.read(100).decode("utf-8", errors="ignore").strip().lower()
        
        # Parse response
        if "ok" in response:
            # E-stop NOT pressed - system normal
            return {
                'is_pressed': False,
                'status': 'normal',
                'raw_response': response
            }
        elif "error" in response:
            # E-stop IS pressed - emergency stop active
            return {
                'is_pressed': True,
                'status': 'e_stop_active',
                'raw_response': response
            }
        else:
            # Unknown response
            return {
                'is_pressed': None,
                'status': f'Unknown response: {response[:20]}',
                'raw_response': response
            }
    
    except serial.SerialException as e:
        return {
            'is_pressed': None,
            'status': 'Serial error',
            'raw_response': str(e)
        }
    except Exception as e:
        return {
            'is_pressed': None,
            'status': f'Error: {str(e)[:30]}',
            'raw_response': ''
        }
    finally:
        if close_after and ser and ser.is_open:
            ser.close()
# ========== NEW: Step-by-Step Execution (Upgrade #3) ==========

class StepExecutor:
    """
    Helper class for step-by-step program execution.
    Allows pausing between steps for debugging and teaching.
    """
    def __init__(self, program: Program):
        self.program = program
        self.current_step = 0
        self.ser = None
        self.is_running = False
        self.is_paused = False
        self.speed_override = 1.0  # Speed override (default 100%)    
    def start(self):
        """Open serial port and prepare for execution."""
        if self.ser is None or not self.ser.is_open:
            self.ser = open_port()
        self.is_running = True
        self.is_paused = False
        self.current_step = 0
        
    def execute_next_step(self) -> dict:
        """
        Execute the next step in the program.
        
        Returns: {
            'step_index': int,           # Current step number (0-based)
            'total_steps': int,          # Total steps in program
            'completed': bool,           # True if program finished
            'step': Step or None,        # The step that was executed
            'status': str,               # Status message
            'error': str or None         # Error message if failed
        }
        """
        if not self.is_running:
            return {
                'step_index': 0,
                'total_steps': len(self.program.steps),
                'completed': False,
                'step': None,
                'status': 'Not started',
                'error': 'Executor not started'
            }
        
        if self.current_step >= len(self.program.steps):
            # Program complete
            return {
                'step_index': self.current_step,
                'total_steps': len(self.program.steps),
                'completed': True,
                'step': None,
                'status': 'Program completed',
                'error': None
            }
        
        try:
            # Get current step
            step = self.program.steps[self.current_step]
            
            print(f"--- Executing Step {self.current_step + 1} / {len(self.program.steps)} ---")
            
            # Execute DO0 (gripper) command first if set
            do_cmd = build_do0(step)
            if do_cmd:
                send_command(self.ser, do_cmd)
            
            # Execute XYZ movement
            move_cmd = build_move(step, self.speed_override if hasattr(self, 'speed_override') else 1.0)
            if move_cmd:
                send_command(self.ser, move_cmd)
            
            # Delay after step
            time.sleep(step.delay)
            
            # Prepare result
            result = {
                'step_index': self.current_step,
                'total_steps': len(self.program.steps),
                'completed': False,
                'step': step,
                'status': f'Executed step {self.current_step + 1}',
                'error': None
            }
            
            # Move to next step
            self.current_step += 1
            
            # Check if program completed
            if self.current_step >= len(self.program.steps):
                result['completed'] = True
                result['status'] = 'Program completed'
            
            return result
            
        except Exception as e:
            return {
                'step_index': self.current_step,
                'total_steps': len(self.program.steps),
                'completed': False,
                'step': step if 'step' in locals() else None,
                'status': 'Error',
                'error': str(e)
            }
    
    def reset(self):
        """Reset to first step without closing port."""
        self.current_step = 0
        self.is_paused = False
    
    def stop(self):
        """Stop execution and close serial port."""
        self.is_running = False
        self.is_paused = False
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Serial port closed.")
        self.ser = None
    
    def get_status(self) -> dict:
        """Get current execution status."""
        return {
            'current_step': self.current_step,
            'total_steps': len(self.program.steps),
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'progress_percent': (self.current_step / len(self.program.steps) * 100) 
                               if len(self.program.steps) > 0 else 0
        }
def check_estop() -> bool:
    """
    Check if E-stop is active using G14 protocol.
    
    Returns:
        bool: True if E-stop is NOT active (safe to move), False if active
    """
    try:
        ser = open_port()
        # Send G14 emergency stop query command
        cmd = "0x550xAA G14 0xAA0x55\r\n"
        ser.write(cmd.encode('utf-8'))
        
        # Wait for response
        time.sleep(0.2)
        response = ser.read(100).decode('utf-8', errors='ignore').strip().lower()
        ser.close()
        
        # Parse response
        if "ok" in response:
            return True  # E-stop NOT pressed - safe to move
        elif "error" in response:
            return False  # E-stop IS pressed - emergency stop active
        else:
            return True  # Default to safe
        
    except Exception as e:
        print(f"E-stop check error: {e}")
        return True  # Default to safe
