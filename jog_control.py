"""
Jog Control Window for Manual Robot Movement
"""

import tkinter as tk
from tkinter import ttk, messagebox
from config import *
from serial_comm import query_position, check_estop
from config import *
import time
import threading
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
        
        # Continuous movement state
        self.is_moving = False
        self.move_direction = None
        self.move_axis = None
        self.move_thread = None
        
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
        """Build movement control buttons with press/release for continuous movement."""
        frame = ttk.LabelFrame(self.scrollable_frame, text="🎮 Movement Controls (Press & Hold)")
        frame.pack(fill="x", padx=10, pady=5)
        
        # Info label
        info_label = tk.Label(frame, text="Press and hold buttons for continuous movement", 
                             font=("Arial", 8), fg="#7f8c8d")
        info_label.pack(pady=3)
        
        # XY Plane
        tk.Label(frame, text="XY Plane:", font=("Arial", 9, "bold")).pack(pady=5)
        
        xy_grid = tk.Frame(frame)
        xy_grid.pack(pady=5)
        
        # Y+ button
        btn_y_up = tk.Button(xy_grid, text="▲\nY+", width=8, bg="#3498db", fg="white",
                            font=("Arial", 10, "bold"), activebackground="#2980b9")
        btn_y_up.grid(row=0, column=1, padx=2, pady=2)
        btn_y_up.bind("<ButtonPress-1>", lambda e: self.on_button_press('Y', 1))
        btn_y_up.bind("<ButtonRelease-1>", lambda e: self.on_button_release())
        
        # X- button
        btn_x_left = tk.Button(xy_grid, text="◀\nX-", width=8, bg="#3498db", fg="white",
                              font=("Arial", 10, "bold"), activebackground="#2980b9")
        btn_x_left.grid(row=1, column=0, padx=2, pady=2)
        btn_x_left.bind("<ButtonPress-1>", lambda e: self.on_button_press('X', -1))
        btn_x_left.bind("<ButtonRelease-1>", lambda e: self.on_button_release())
        
        # HOME button
        ttk.Button(xy_grid, text="🏠\nHOME", command=self.go_home,
                  width=8).grid(row=1, column=1, padx=2, pady=2)
        
        # X+ button
        btn_x_right = tk.Button(xy_grid, text="▶\nX+", width=8, bg="#3498db", fg="white",
                               font=("Arial", 10, "bold"), activebackground="#2980b9")
        btn_x_right.grid(row=1, column=2, padx=2, pady=2)
        btn_x_right.bind("<ButtonPress-1>", lambda e: self.on_button_press('X', 1))
        btn_x_right.bind("<ButtonRelease-1>", lambda e: self.on_button_release())
        
        # Y- button
        btn_y_down = tk.Button(xy_grid, text="▼\nY-", width=8, bg="#3498db", fg="white",
                              font=("Arial", 10, "bold"), activebackground="#2980b9")
        btn_y_down.grid(row=2, column=1, padx=2, pady=2)
        btn_y_down.bind("<ButtonPress-1>", lambda e: self.on_button_press('Y', -1))
        btn_y_down.bind("<ButtonRelease-1>", lambda e: self.on_button_release())
        
        # Z Axis
        tk.Label(frame, text="Z Axis:", font=("Arial", 9, "bold")).pack(pady=5)
        
        z_frame = tk.Frame(frame)
        z_frame.pack(pady=5)
        
        # Z+ button
        btn_z_up = tk.Button(z_frame, text="▲\nZ+", width=10, bg="#e74c3c", fg="white",
                            font=("Arial", 10, "bold"), activebackground="#c0392b")
        btn_z_up.pack(side="left", padx=5)
        btn_z_up.bind("<ButtonPress-1>", lambda e: self.on_button_press('Z', 1))
        btn_z_up.bind("<ButtonRelease-1>", lambda e: self.on_button_release())
        
        # Z- button
        btn_z_down = tk.Button(z_frame, text="▼\nZ-", width=10, bg="#e74c3c", fg="white",
                              font=("Arial", 10, "bold"), activebackground="#c0392b")
        btn_z_down.pack(side="left", padx=5)
        btn_z_down.bind("<ButtonPress-1>", lambda e: self.on_button_press('Z', -1))
        btn_z_down.bind("<ButtonRelease-1>", lambda e: self.on_button_release())
        
        # Stop button
        tk.Label(frame, text="", font=("Arial", 3)).pack(pady=2)
        stop_btn = tk.Button(frame, text="⏹ STOP", width=20, bg="#e74c3c", fg="white",
                            font=("Arial", 11, "bold"), command=self.stop_movement,
                            activebackground="#c0392b")
        stop_btn.pack(pady=5)
    
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
    
    def send_protocol(self, cmd: str, show_errors=True):
        """Send protocol command to serial port with error handling."""
        import time
        
        max_retries = 3
        retry_delay = 0.01  # 10ms between retries
        
        for attempt in range(max_retries):
            try:
                from serial_comm import open_port, list_available_ports
                
                ser = open_port()
                if ser is None or not ser.is_open:
                    if show_errors and attempt == max_retries - 1:
                        messagebox.showerror(
                            "Serial Error",
                            "Failed to open serial port.\n\n"
                            "Troubleshooting:\n"
                            "1. Check if robot is connected via USB\n"
                            "2. Close any other applications using the port\n"
                            "3. Check Device Manager for COM port\n"
                            "4. Update/reinstall USB drivers"
                        )
                    return None
                
                ser.write(cmd.encode('utf-8'))
                time.sleep(0.01)  # Short wait for response
                response = ser.read(100) if ser.in_waiting > 0 else None
                ser.close()
                return response
            
            except PermissionError as e:
                # Port temporarily locked - retry silently
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    # Only show error on final retry if enabled
                    if show_errors:
                        messagebox.showerror(
                            "Port Access Denied",
                            f"Cannot access COM3 - Port is in use.\n\n"
                            f"Solution:\n"
                            f"• Close Serial Monitor in Arduino IDE\n"
                            f"• Close other terminal applications\n"
                            f"• Restart the application"
                        )
                    return None
            
            except FileNotFoundError:
                available = list_available_ports()
                if show_errors and attempt == max_retries - 1:
                    messagebox.showerror(
                        "Port Not Found",
                        f"COM3 not found.\n\n"
                        f"Available ports: {available if available else 'None'}\n\n"
                        f"Check:\n"
                        f"• USB cable connection\n"
                        f"• Device Manager\n"
                        f"• Run diagnose_serial.py"
                    )
                return None
            
            except Exception as e:
                if show_errors and attempt == max_retries - 1:
                    messagebox.showerror(
                        "Serial Communication Error",
                        f"Error: {str(e)}\n\n"
                        f"Check USB connection and Device Manager"
                    )
                return None
        
        return None
    
    def on_button_press(self, axis, direction):
        """Called when user presses and holds a movement button."""
        if self.is_moving:
            self.stop_movement()  # Stop any current movement
        
        self.is_moving = True
        self.move_axis = axis
        self.move_direction = direction
        
        # Start continuous movement in a separate thread
        self.move_thread = threading.Thread(target=self.continuous_move_loop, daemon=True)
        self.move_thread.start()
    
    def on_button_release(self):
        """Called when user releases the movement button."""
        self.stop_movement()
    
    def stop_movement(self):
        """Stop all movement."""
        self.is_moving = False
        
        # Send stop command to robot
        try:
            self.send_protocol("0xff0xfe0x020xfd0xfc")  # Stop command
        except:
            pass
        
        # Wait for thread to finish
        if self.move_thread and self.move_thread.is_alive():
            time.sleep(0.1)
    
    def continuous_move_loop(self):
        """Continuously send movement commands while button is held."""
        try:
            # Scale distance to protocol F range (0-800)
            f_value = int(self.jog_speed * 8)  # Use speed slider (10-100% -> 80-800)
            f_value = max(50, min(800, f_value))
            
            # MANUAL MODE COMMANDS (from protocol doc)
            cmd_map = {
                ('X', 1): f"0xff0xfe0x04F{f_value}0xfd0xfc",  # X+ clockwise
                ('X', -1): f"0xff0xfe0x03F{f_value}0xfd0xfc", # X- counterclockwise  
                ('Y', 1): f"0xff0xfe0x06F{f_value}0xfd0xfc",  # Y+ forward
                ('Y', -1): f"0xff0xfe0x05F{f_value}0xfd0xfc", # Y- backward
                ('Z', 1): f"0xff0xfe0x08F{f_value}0xfd0xfc",  # Z+ forward
                ('Z', -1): f"0xff0xfe0x07F{f_value}0xfd0xfc", # Z- backward
            }
            
            cmd = cmd_map[(self.move_axis, self.move_direction)]
            print(f"🎮 Continuous jog {self.move_axis}{self.move_direction} F{f_value}")
            
            # Send movement command repeatedly while button is held
            # Use show_errors=False to suppress error dialogs during rapid sends
            while self.is_moving:
                self.send_protocol(cmd, show_errors=False)
                time.sleep(0.05)  # Update every 50ms for smooth movement
        
        except Exception as e:
            print(f"Continuous move error: {e}")

    
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
        
        try:
            # Build commands with protocol wrapper
            feedrate = 200  # Safe default
            
            # Move Z up first
            cmd1 = f"0x550xAA G01 Z{WORKSPACE_LIMITS['Z']['max']} F{feedrate} 0xAA0x55"
            self.send_protocol(cmd1)
            
            # Move XY to home
            cmd2 = f"0x550xAA G01 X0 Y0 F{feedrate} 0xAA0x55"
            self.send_protocol(cmd2)
            
            # Move Z to home
            cmd3 = f"0x550xAA G01 Z0 F{feedrate} 0xAA0x55"
            self.send_protocol(cmd3)
            
            self.current_pos = {'x': 0.0, 'y': 0.0, 'z': 0.0}
            self.update_position_display()
            messagebox.showinfo("Home", "Robot moved to home position")
        except Exception as e:
            messagebox.showerror("Go Home Error", str(e))
    
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
