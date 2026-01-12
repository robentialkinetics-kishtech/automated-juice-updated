"""
Jog Control Window for Manual Robot Movement
"""

import tkinter as tk
from tkinter import ttk, messagebox
from config import *
from serial_comm import send_command, query_position, check_estop
from config import *
import time
from steps import MoveStep

class JogControlWindow(tk.Toplevel):
    """Manual jog control interface."""
    
    def __init__(self, parent, program=None):
        """Initialize jog control window."""
        super().__init__(parent)
        
        self.program = program
        self.title("🕹️ Jog Control")
        self.geometry("550x600")  # Fixed compact size
        self.resizable(False, False)
        
        # Position monitoring
        self.position_monitor_active = False
        self.monitor_job = None
        self.current_pos = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        
        # Settings
        self.jog_distance = 10.0
        self.jog_speed = 50
        self.workspace_limits = WORKSPACE_LIMITS
        self.position_monitor_active = False
        # Create scrollable container
        container = tk.Frame(self)
        container.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        
        self.scrollable_frame = ttk.Frame(canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=530)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Build UI
        self._build_ui()
        
        # Keyboard
        self.bind("<KeyPress>", self.on_key_press)
        
        # Start monitoring
        # self.start_position_monitor()
                                  
        
        # Close handler
        self.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def _build_ui(self):
        """Build user interface."""
        # Header
        header = tk.Frame(self.scrollable_frame, bg="#2c3e50", height=60)
        header.pack(fill="x")
        
        tk.Label(
            header,
            text="🕹️ Jog Control",
            font=("Arial", 16, "bold"),
            bg="#2c3e50",
            fg="white"
        ).pack(pady=15)
        
        # Position Display
        self._build_position_display()
        
        # Jog Settings
        self._build_jog_settings()
        
        # Movement Controls
        self._build_movement_controls()
        
        # Action Buttons
        self._build_action_buttons()
    
    def _build_position_display(self):
        """Build position display section."""
        frame = ttk.LabelFrame(self.scrollable_frame, text="📍 Current Position")
        frame.pack(fill="x", padx=10, pady=5)
        
        pos_frame = tk.Frame(frame, bg="#34495e", padx=10, pady=10)
        pos_frame.pack(fill="x", padx=5, pady=5)
        
        self.pos_x_var = tk.StringVar(value="0.0")
        self.pos_y_var = tk.StringVar(value="0.0")
        self.pos_z_var = tk.StringVar(value="0.0")
        
        for i, (axis, var, color) in enumerate([
            ("X:", self.pos_x_var, "#3498db"),
            ("Y:", self.pos_y_var, "#2ecc71"),
            ("Z:", self.pos_z_var, "#e74c3c")
        ]):
            tk.Label(pos_frame, text=axis, font=("Arial", 12, "bold"),
                    bg="#34495e", fg="white").grid(row=0, column=i*2, padx=5)
            tk.Label(pos_frame, textvariable=var, font=("Arial", 12, "bold"),
                    bg="#34495e", fg=color, width=8).grid(row=0, column=i*2+1, padx=5)
    
    def _build_jog_settings(self):
        """Build jog settings section."""
        frame = ttk.LabelFrame(self.scrollable_frame, text="⚙️ Jog Settings")
        frame.pack(fill="x", padx=10, pady=5)
        
        # Distance
        dist_frame = tk.Frame(frame)
        dist_frame.pack(fill="x", padx=5, pady=5)
        
        tk.Label(dist_frame, text="Jog Distance:").pack(side="left", padx=5)
        
        self.distance_var = tk.StringVar(value="10")
        distance_combo = ttk.Combobox(
            dist_frame,
            textvariable=self.distance_var,
            values=["1", "5", "10", "20", "50", "100"],
            width=8,
            state="readonly"
        )
        distance_combo.pack(side="left", padx=5)
        distance_combo.bind("<<ComboboxSelected>>", self.on_distance_change)
        
        tk.Label(dist_frame, text="mm").pack(side="left")
        
        # Speed
        speed_frame = tk.Frame(frame)
        speed_frame.pack(fill="x", padx=5, pady=5)
        
        tk.Label(speed_frame, text="Jog Speed:").pack(side="left", padx=5)
        
        self.speed_label = tk.Label(speed_frame, text="50", 
                                    font=("Arial", 10, "bold"),
                                    bg="#2ecc71", fg="white",
                                    width=5, padx=5, pady=2)
        self.speed_label.pack(side="left", padx=5)
        
        tk.Label(speed_frame, text="%").pack(side="left")
        
        # Speed slider
        self.speed_slider = tk.Scale(
            frame,
            from_=10,
            to=100,
            orient="horizontal",
            showvalue=False,
            command=self.on_speed_change
        )
        self.speed_slider.set(50)
        self.speed_slider.pack(fill="x", padx=5, pady=5)
        
        # Speed buttons
        speed_btns = tk.Frame(frame)
        speed_btns.pack(fill="x", padx=5, pady=2)
        
        for speed in [25, 50, 75, 100]:
            ttk.Button(
                speed_btns,
                text=f"{speed}%",
                command=lambda s=speed: self.set_speed(s),
                width=8
            ).pack(side="left", padx=2, expand=True)
    
    def _build_movement_controls(self):
        """Build movement control buttons."""
        frame = ttk.LabelFrame(self.scrollable_frame, text="🎮 Movement Controls")
        frame.pack(fill="x", padx=10, pady=5)
        
        # XY Plane
        tk.Label(frame, text="XY Plane:", font=("Arial", 9, "bold")).pack(pady=5)
        
        xy_grid = tk.Frame(frame)
        xy_grid.pack(pady=5)
        
        # Y+
        ttk.Button(xy_grid, text="▲\nY+", command=lambda: self.jog_move('Y', 1),
                  width=8).grid(row=0, column=1, padx=2, pady=2)
        
        # X-, HOME, X+
        ttk.Button(xy_grid, text="◀\nX-", command=lambda: self.jog_move('X', -1),
                  width=8).grid(row=1, column=0, padx=2, pady=2)
        ttk.Button(xy_grid, text="🏠\nHOME", command=self.go_home,
                  width=8).grid(row=1, column=1, padx=2, pady=2)
        ttk.Button(xy_grid, text="▶\nX+", command=lambda: self.jog_move('X', 1),
                  width=8).grid(row=1, column=2, padx=2, pady=2)
        
        # Y-
        ttk.Button(xy_grid, text="▼\nY-", command=lambda: self.jog_move('Y', -1),
                  width=8).grid(row=2, column=1, padx=2, pady=2)
        
        # Z Axis
        tk.Label(frame, text="Z Axis:", font=("Arial", 9, "bold")).pack(pady=5)
        
        z_frame = tk.Frame(frame)
        z_frame.pack(pady=5)
        
        ttk.Button(z_frame, text="▲\nZ+", command=lambda: self.jog_move('Z', 1),
                  width=10).pack(side="left", padx=5)
        ttk.Button(z_frame, text="▼\nZ-", command=lambda: self.jog_move('Z', -1),
                  width=10).pack(side="left", padx=5)
    
    def _build_action_buttons(self):
        """Build action buttons."""
        frame = tk.Frame(self.scrollable_frame)
        frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(
            frame,
            text="📍 Teach Position",
            command=self.teach_position
        ).pack(side="left", expand=True, padx=5)
        
        ttk.Button(
            frame,
            text="🏠 Go Home",
            command=self.go_home
        ).pack(side="left", expand=True, padx=5)
    
    # --- Event Handlers ---
    
    def on_distance_change(self, event=None):
        """Handle distance change."""
        self.jog_distance = float(self.distance_var.get())
    
    def on_speed_change(self, value):
        """Handle speed slider change."""
        self.jog_speed = int(float(value))
        self.speed_label.config(text=str(self.jog_speed))
    
    def set_speed(self, speed):
        """Set speed to specific value."""
        self.speed_slider.set(speed)
        self.jog_speed = speed
        self.speed_label.config(text=str(speed))
    
    def jog_move(self, axis, direction):
        """Execute jog movement using MANUAL single-axis commands."""
        try:
            # Stop any previous movement first
            send_command("0xff0xfe0x020xfd0xfc")  # Emergency stop
            time.sleep(0.1)
            
            # Manual mode single-axis commands (0x03-0x08)
            # F = movement amount (0-800), larger = bigger movement
            movement_amount = int(self.jog_distance * 10)  # Scale to 0-800 range
            movement_amount = max(50, min(800, movement_amount))
            
            cmd_map = {
                ('X', 1): "0xff0xfe0x040xfd0xfc",  # X+ (clockwise)
                ('X', -1): "0xff0xfe0x030xfd0xfc", # X- (counterclockwise)
                ('Y', 1): "0xff0xfe0x060xfd0xfc",  # Y+ (forward)
                ('Y', -1): "0xff0xfe0x050xfd0xfc", # Y- (backward)
                ('Z', 1): "0xff0xfe0x080xfd0xfc",  # Z+ (forward)
                ('Z', -1): "0xff0xfe0x070xfd0xfc"  # Z- (backward)
            }
            
            cmd = cmd_map.get((axis, direction))
            if not cmd:
                print("Invalid axis/direction")
                return
            
            print(f"Jog {axis}{direction}: {cmd}")
            
            # Send command
            result = send_command(cmd)
            print(f"Result: {result}")
            
            # Update display after small delay
            self.after(200, self.update_position_display)
            
        except Exception as e:
            print(f"Jog error: {e}")



    
    def check_workspace_limits(self, pos):
        """Check if position is within workspace limits."""
        if pos['x'] < WORKSPACE_LIMITS['X']['min'] or pos['x'] > WORKSPACE_LIMITS['X']['max']:
            return False
        if pos['y'] < WORKSPACE_LIMITS['Y']['min'] or pos['y'] > WORKSPACE_LIMITS['Y']['max']:
            return False
        if pos['z'] < WORKSPACE_LIMITS['Z']['min'] or pos['z'] > WORKSPACE_LIMITS['Z']['max']:
            return False
        return True
    
    def go_home(self):
        """Move to home position."""
        if not check_estop():
            messagebox.showerror("E-Stop", "Release E-stop first!")
            return
        
        # Move Z up first
        send_command(f"G01 Z{WORKSPACE_LIMITS['Z']['max']} F{MAX_FEEDRATE}")
        # Move XY to home
        send_command(f"G01 X0 Y0 F{MAX_FEEDRATE}")
        # Move Z to home
        send_command(f"G01 Z0 F{MAX_FEEDRATE}")
        
        self.current_pos = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self.update_position_display()
    
    def teach_position(self):
        """Add current position to program."""
        try:
            if self.program is None:
                messagebox.showinfo("No Program", "No program loaded!")
                return
            
            # Use safe feedrate (no MAX_FEEDRATE dependency)
            feedrate = int(500 * (self.jog_speed / 100))  # Max 500 for ZKBot
            feedrate = max(1, min(500, feedrate))
            
            # Create MoveStep
            step = MoveStep(
                x=self.current_pos['x'],
                y=self.current_pos['y'],
                z=self.current_pos['z'],
                feedrate=feedrate
            )
            
            self.program.add_step(step)
            messagebox.showinfo("Success", 
                f"Position taught!\n"
                f"X: {self.current_pos['x']:.1f}\n"
                f"Y: {self.current_pos['y']:.1f}\n"
                f"Z: {self.current_pos['z']:.1f}\n"
                f"Feedrate: {feedrate}")
                
        except Exception as e:
            print(f"Teach error: {e}")
            messagebox.showerror("Error", f"Failed to teach position: {e}")

    def on_key_press(self, event):
        """Handle keyboard shortcuts."""
        key = event.keysym
        
        if key == "Up":
            self.jog_move('Y', 1)
        elif key == "Down":
            self.jog_move('Y', -1)
        elif key == "Left":
            self.jog_move('X', -1)
        elif key == "Right":
            self.jog_move('X', 1)
        elif key == "Prior":  # Page Up
            self.jog_move('Z', 1)
        elif key == "Next":  # Page Down
            self.jog_move('Z', -1)
        elif key == "Home":
            self.go_home()
    
    # --- Position Monitoring ---
    
    def start_position_monitor(self):
        """Start position monitoring."""
        self.position_monitor_active = True
        self.update_position_loop()
    
    def stop_position_monitor(self):
        """Stop position monitoring."""
        self.position_monitor_active = False
        if self.monitor_job:
            self.after_cancel(self.monitor_job)
    
    def update_position_loop(self):
        """Position update loop."""
        if not self.position_monitor_active:
            return
        
        try:
            pos = query_position()
            if pos['x'] is not None:
                self.current_pos = pos
                self.update_position_display()
        except:
            pass
        
        self.monitor_job = self.after(500, self.update_position_loop)
    
    def update_position_display(self):
        """Update position labels."""
        self.pos_x_var.set(f"{self.current_pos['x']:.1f}")
        self.pos_y_var.set(f"{self.current_pos['y']:.1f}")
        self.pos_z_var.set(f"{self.current_pos['z']:.1f}")
    
    def on_close(self):
        """Handle window close."""
        self.stop_position_monitor()
        self.destroy()


def open_jog_control(parent, program=None):
    """Open jog control window."""
    return JogControlWindow(parent, program)
