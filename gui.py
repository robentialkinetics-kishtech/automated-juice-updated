# gui.py (COMPLETE - Phase 3: Order Queue Added)
#
# All previous upgrades + Order Queue System

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Canvas, Scrollbar
from typing import Optional
import threading
import time

from models import Step, Program
from serial_comm import run_program, query_position, check_emergency_stop, StepExecutor
from config import PROGRAMS_DIR, SPEED_OVERRIDE_PERCENT, JUICE_FLAVORS, MAX_ORDER_QUANTITY
from order_queue import OrderQueue, estimate_program_time, format_time
from jog_control import JogControlWindow


class MainWindow(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.master.title("ZKBot Juice Kiosk v8")
        
        # Set minimum window size
        self.master.geometry("1300x700")
        self.master.minsize(1100, 600)
        
        self.pack(fill="both", expand=True)

        self.program = Program("unnamed")
        self.current_path = None
        
        # State variables
        self.monitor_active = False
        self.monitor_job = None
        self.estop_blink_state = False
        self.estop_blink_job = None
        self.step_executor = None
        self.execution_mode = tk.StringVar(value="normal")
        self.debug_running = False
        self.speed_override = tk.DoubleVar(value=SPEED_OVERRIDE_PERCENT)
        self.clipboard_step = None
        
        # NEW: Order Queue variables
        self.order_queue = OrderQueue()
        self.queue_processing = False
        self.queue_thread = None
        self.current_order_juice = 0  # Current juice number in order
        self.program_lock = threading.Lock()  # Thread safety for program access
        
        self._build_widgets()
    def _build_widgets(self):
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        # --- LEFT: Steps table ---
        left_frame = tk.Frame(self)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        left_frame.rowconfigure(0, weight=1)
        left_frame.columnconfigure(0, weight=1)
        
        columns = ("cmd", "x", "y", "z", "f", "delay", "do0")
        self.tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=25)
        headings = {"cmd": "Cmd", "x": "X", "y": "Y", "z": "Z", "f": "F", "delay": "Delay", "do0": "DO0"}
        for col, text in headings.items():
            self.tree.heading(col, text=text)
            self.tree.column(col, width=70, anchor="center")

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self.on_select_step)
        
        # Keyboard shortcuts
        self.tree.bind("<Control-c>", lambda e: self.on_copy_step())
        self.tree.bind("<Control-v>", lambda e: self.on_paste_step())
        self.tree.bind("<Control-d>", lambda e: self.on_duplicate_step())
        self.tree.bind("<Control-Up>", lambda e: self.on_move_up())
        self.tree.bind("<Control-Down>", lambda e: self.on_move_down())
        self.tree.bind("<Control-a>", lambda e: self.on_select_all())
        self.tree.bind("<Control-Shift-Delete>", lambda e: self.on_clear_all())
        
        # Scrollbar for tree
        tree_scroll = ttk.Scrollbar(left_frame, orient="vertical", command=self.tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scroll.set)

        # --- RIGHT: Scrollable control panel ---
        right_frame = tk.Frame(self)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        right_frame.rowconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)
        
        # Create canvas with scrollbar
        canvas = Canvas(right_frame)
        scrollbar = Scrollbar(right_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Enable mousewheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)

        # --- Build all panels in order ---
        self._build_order_queue_panel(scrollable_frame)      # NEW!
        self._build_speed_override_panel(scrollable_frame)
        self._build_estop_panel(scrollable_frame)
        self._build_position_panel(scrollable_frame)
        self._build_debug_panel(scrollable_frame)
        self._build_step_editor_panel(scrollable_frame)
        self._build_program_panel(scrollable_frame)
        self._build_run_panel(scrollable_frame)
    # ---------- NEW: Order Queue Panel ----------
    
    def _build_order_queue_panel(self, parent):
        """Build the order queue management panel."""
        queue_frame = ttk.LabelFrame(parent, text="📋 Order Queue")
        queue_frame.pack(fill="x", padx=5, pady=3)
        
        # New Order Section
        new_order_frame = tk.Frame(queue_frame, bg="#ecf0f1", padx=5, pady=5)
        new_order_frame.pack(fill="x", padx=3, pady=3)
        
        tk.Label(new_order_frame, text="New Order:", font=("Arial", 8, "bold"),
                bg="#ecf0f1").grid(row=0, column=0, columnspan=4, sticky="w", pady=2)
        
        # Flavor selector
        tk.Label(new_order_frame, text="Flavor:", font=("Arial", 8), bg="#ecf0f1").grid(
            row=1, column=0, sticky="e", padx=2)
        self.flavor_var = tk.StringVar(value=list(JUICE_FLAVORS.keys())[0])
        self.flavor_combo = ttk.Combobox(new_order_frame, textvariable=self.flavor_var,
                                        values=list(JUICE_FLAVORS.keys()), width=10,
                                        font=("Arial", 8), state="readonly")
        self.flavor_combo.grid(row=1, column=1, sticky="ew", padx=2)
        self.flavor_combo.bind("<<ComboboxSelected>>", lambda e: self.update_order_estimate())
        
        # Quantity selector
        tk.Label(new_order_frame, text="Qty:", font=("Arial", 8), bg="#ecf0f1").grid(
            row=1, column=2, sticky="e", padx=2)
        self.quantity_var = tk.IntVar(value=1)
        self.quantity_spin = ttk.Spinbox(new_order_frame, from_=1, to=MAX_ORDER_QUANTITY,
                                        textvariable=self.quantity_var, width=5,
                                        font=("Arial", 8), command=self.update_order_estimate)
        self.quantity_spin.grid(row=1, column=3, sticky="w", padx=2)
        
        # Estimated time
        self.order_est_var = tk.StringVar(value="Est: 0m 0s")
        tk.Label(new_order_frame, textvariable=self.order_est_var, font=("Arial", 7),
                fg="#7f8c8d", bg="#ecf0f1").grid(row=2, column=0, columnspan=4, pady=2)
        
        # Add to queue button
        self.add_queue_btn = ttk.Button(new_order_frame, text="➕ Add to Queue",
                                       command=self.on_add_to_queue)
        self.add_queue_btn.grid(row=3, column=0, columnspan=4, pady=3, sticky="ew")
        
        new_order_frame.columnconfigure(1, weight=1)
        
        # Queue Display
        queue_display_frame = tk.Frame(queue_frame, bg="#ffffff", padx=5, pady=5)
        queue_display_frame.pack(fill="both", expand=True, padx=3, pady=3)
        
        self.queue_count_var = tk.StringVar(value="Queue (0 orders):")
        tk.Label(queue_display_frame, textvariable=self.queue_count_var,
                font=("Arial", 8, "bold"), bg="#ffffff").pack(anchor="w")
        
        # Queue listbox
        queue_list_frame = tk.Frame(queue_display_frame, bg="#ffffff")
        queue_list_frame.pack(fill="both", expand=True, pady=3)
        
        self.queue_listbox = tk.Listbox(queue_list_frame, height=4, font=("Arial", 8),
                                        bg="#f8f9fa", relief="solid", borderwidth=1)
        self.queue_listbox.pack(side="left", fill="both", expand=True)
        
        queue_scroll = ttk.Scrollbar(queue_list_frame, orient="vertical",
                                     command=self.queue_listbox.yview)
        queue_scroll.pack(side="right", fill="y")
        self.queue_listbox.configure(yscrollcommand=queue_scroll.set)
        
        # Progress Info
        progress_frame = tk.Frame(queue_frame, bg="#e8f4f8", padx=5, pady=5)
        progress_frame.pack(fill="x", padx=3, pady=3)
        
        self.current_order_var = tk.StringVar(value="Current: None")
        tk.Label(progress_frame, textvariable=self.current_order_var, font=("Arial", 8),
                bg="#e8f4f8").pack(anchor="w")
        
        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                           maximum=100, length=200)
        self.progress_bar.pack(fill="x", pady=2)
        
        self.progress_text_var = tk.StringVar(value="Progress: 0%")
        tk.Label(progress_frame, textvariable=self.progress_text_var, font=("Arial", 7),
                fg="#7f8c8d", bg="#e8f4f8").pack(anchor="w")
        
        self.time_remaining_var = tk.StringVar(value="Time Remaining: --")
        tk.Label(progress_frame, textvariable=self.time_remaining_var, font=("Arial", 7),
                fg="#7f8c8d", bg="#e8f4f8").pack(anchor="w")
        
        self.total_queue_time_var = tk.StringVar(value="Total Queue Time: 0m 0s")
        tk.Label(progress_frame, textvariable=self.total_queue_time_var, font=("Arial", 7),
                fg="#7f8c8d", bg="#e8f4f8").pack(anchor="w")
        
        # Control buttons
        btn_frame = tk.Frame(queue_frame)
        btn_frame.pack(fill="x", padx=3, pady=3)
        
        self.start_queue_btn = ttk.Button(btn_frame, text="▶ Start Queue",
                                         command=self.on_start_queue)
        self.start_queue_btn.pack(side="left", padx=1, fill="x", expand=True)
        
        self.stop_queue_btn = ttk.Button(btn_frame, text="⏹ Stop Queue",
                                        command=self.on_stop_queue, state="disabled")
        self.stop_queue_btn.pack(side="left", padx=1, fill="x", expand=True)
        
        ttk.Button(btn_frame, text="🗑️ Clear", command=self.on_clear_queue).pack(
            side="left", padx=1)
    def _build_speed_override_panel(self, parent):
        """Build speed override panel."""
        speed_frame = ttk.LabelFrame(parent, text="⚡ Speed Override")
        speed_frame.pack(fill="x", padx=5, pady=3)
        
        speed_display = tk.Frame(speed_frame, bg="#16a085", padx=8, pady=5)
        speed_display.pack(fill="x", padx=3, pady=3)
        
        tk.Label(speed_display, textvariable=self.speed_override, font=("Arial", 18, "bold"),
                bg="#16a085", fg="white").pack(side="left", padx=3)
        tk.Label(speed_display, text="%", font=("Arial", 14), bg="#16a085", fg="white").pack(side="left")
        
        preset_frame = tk.Frame(speed_frame)
        preset_frame.pack(fill="x", padx=3, pady=2)
        
        presets = [("25%", 25), ("50%", 50), ("100%", 100), ("150%", 150), ("200%", 200)]
        for i, (label, value) in enumerate(presets):
            tk.Button(preset_frame, text=label, command=lambda v=value: self.set_speed_preset(v),
                     font=("Arial", 7), width=5, height=1).grid(row=0, column=i, padx=1, sticky="ew")
            preset_frame.columnconfigure(i, weight=1)
        
        self.speed_slider = tk.Scale(speed_frame, from_=10, to=200, orient="horizontal",
                                     variable=self.speed_override, command=self.on_speed_change,
                                     showvalue=False, length=200)
        self.speed_slider.pack(fill="x", padx=3, pady=2)
        
        self.speed_info = tk.Label(speed_frame, text="F20 → F10 (50%)", font=("Arial", 7), fg="#7f8c8d")
        self.speed_info.pack(pady=1)

    def _build_estop_panel(self, parent):
        """Build E-Stop panel."""
        estop_frame = ttk.LabelFrame(parent, text="⚠️ E-Stop")
        estop_frame.pack(fill="x", padx=5, pady=3)
        
        self.estop_display = tk.Frame(estop_frame, bg="#34495e", padx=6, pady=5)
        self.estop_display.pack(fill="x", padx=3, pady=3)
        
        self.estop_icon = tk.Label(self.estop_display, text="●", font=("Arial", 16),
                                   bg="#34495e", fg="gray")
        self.estop_icon.pack(side="left", padx=5)
        
        self.estop_status_text = tk.Label(self.estop_display, text="Not Checked",
                                         font=("Arial", 9, "bold"), bg="#34495e", fg="white")
        self.estop_status_text.pack(side="left")
        
        ttk.Button(estop_frame, text="Check", command=self.check_estop_status).pack(fill="x", padx=3, pady=2)

    def _build_position_panel(self, parent):
        """Build position monitoring panel."""
        pos_frame = ttk.LabelFrame(parent, text="📍 Position")
        pos_frame.pack(fill="x", padx=5, pady=3)
        
        display_frame = tk.Frame(pos_frame, bg="#2c3e50", padx=5, pady=4)
        display_frame.pack(fill="x", padx=3, pady=3)
        
        self.pos_x_var = tk.StringVar(value="---")
        self.pos_y_var = tk.StringVar(value="---")
        self.pos_z_var = tk.StringVar(value="---")
        
        for i, (label, var, color) in enumerate([
            ("X:", self.pos_x_var, "#3498db"),
            ("Y:", self.pos_y_var, "#2ecc71"),
            ("Z:", self.pos_z_var, "#e74c3c")
        ]):
            tk.Label(display_frame, text=label, font=("Arial", 8), bg="#2c3e50", fg="#ecf0f1").grid(
                row=i, column=0, sticky="e")
            tk.Label(display_frame, textvariable=var, font=("Courier", 9), bg="#2c3e50",
                    fg=color, width=8).grid(row=i, column=1, padx=2)
        
        btn_frame = tk.Frame(pos_frame)
        btn_frame.pack(fill="x", padx=3, pady=2)
        
        self.start_monitor_btn = ttk.Button(btn_frame, text="▶", command=self.start_monitor, width=3)
        self.start_monitor_btn.pack(side="left", padx=1)
        
        self.stop_monitor_btn = ttk.Button(btn_frame, text="⏸", command=self.stop_monitor,
                                          state="disabled", width=3)
        self.stop_monitor_btn.pack(side="left", padx=1)

    def _build_debug_panel(self, parent):
        """Build debug mode panel."""
        debug_frame = ttk.LabelFrame(parent, text="🐛 Debug")
        debug_frame.pack(fill="x", padx=5, pady=3)
        
        mode_frame = tk.Frame(debug_frame)
        mode_frame.pack(fill="x", padx=3, pady=2)
        
        tk.Radiobutton(mode_frame, text="Normal", variable=self.execution_mode,
                      value="normal", font=("Arial", 7)).pack(side="left", padx=2)
        tk.Radiobutton(mode_frame, text="Step-by-Step", variable=self.execution_mode,
                      value="step", font=("Arial", 7)).pack(side="left", padx=2)
        
        self.debug_step_var = tk.StringVar(value="- / -")
        self.debug_status_var = tk.StringVar(value="Ready")
        
        tk.Label(debug_frame, textvariable=self.debug_step_var, font=("Arial", 8, "bold")).pack()
        tk.Label(debug_frame, textvariable=self.debug_status_var, font=("Arial", 7),
                fg="#7f8c8d").pack()
        
        debug_btns = tk.Frame(debug_frame)
        debug_btns.pack(fill="x", padx=3, pady=2)
        
        self.next_step_btn = ttk.Button(debug_btns, text="▶ Next", command=self.execute_next_step,
                                       state="disabled")
        self.next_step_btn.pack(side="left", padx=1, fill="x", expand=True)
        
        self.stop_debug_btn = ttk.Button(debug_btns, text="⏹", command=self.stop_debug_execution,
                                        state="disabled", width=3)
        self.stop_debug_btn.pack(side="left", padx=1)
    def _build_speed_override_panel(self, parent):
        """Build speed override panel."""
        speed_frame = ttk.LabelFrame(parent, text="⚡ Speed Override")
        speed_frame.pack(fill="x", padx=5, pady=3)
        
        speed_display = tk.Frame(speed_frame, bg="#16a085", padx=8, pady=5)
        speed_display.pack(fill="x", padx=3, pady=3)
        
        tk.Label(speed_display, textvariable=self.speed_override, font=("Arial", 18, "bold"),
                bg="#16a085", fg="white").pack(side="left", padx=3)
        tk.Label(speed_display, text="%", font=("Arial", 14), bg="#16a085", fg="white").pack(side="left")
        
        preset_frame = tk.Frame(speed_frame)
        preset_frame.pack(fill="x", padx=3, pady=2)
        
        presets = [("25%", 25), ("50%", 50), ("100%", 100), ("150%", 150), ("200%", 200)]
        for i, (label, value) in enumerate(presets):
            tk.Button(preset_frame, text=label, command=lambda v=value: self.set_speed_preset(v),
                     font=("Arial", 7), width=5, height=1).grid(row=0, column=i, padx=1, sticky="ew")
            preset_frame.columnconfigure(i, weight=1)
        
        self.speed_slider = tk.Scale(speed_frame, from_=10, to=200, orient="horizontal",
                                     variable=self.speed_override, command=self.on_speed_change,
                                     showvalue=False, length=200)
        self.speed_slider.pack(fill="x", padx=3, pady=2)
        
        self.speed_info = tk.Label(speed_frame, text="F20 → F10 (50%)", font=("Arial", 7), fg="#7f8c8d")
        self.speed_info.pack(pady=1)

    def _build_estop_panel(self, parent):
        """Build E-Stop panel."""
        estop_frame = ttk.LabelFrame(parent, text="⚠️ E-Stop")
        estop_frame.pack(fill="x", padx=5, pady=3)
        
        self.estop_display = tk.Frame(estop_frame, bg="#34495e", padx=6, pady=5)
        self.estop_display.pack(fill="x", padx=3, pady=3)
        
        self.estop_icon = tk.Label(self.estop_display, text="●", font=("Arial", 16),
                                   bg="#34495e", fg="gray")
        self.estop_icon.pack(side="left", padx=5)
        
        self.estop_status_text = tk.Label(self.estop_display, text="Not Checked",
                                         font=("Arial", 9, "bold"), bg="#34495e", fg="white")
        self.estop_status_text.pack(side="left")
        
        ttk.Button(estop_frame, text="Check", command=self.check_estop_status).pack(fill="x", padx=3, pady=2)

    def _build_position_panel(self, parent):
        """Build position monitoring panel."""
        pos_frame = ttk.LabelFrame(parent, text="📍 Position")
        pos_frame.pack(fill="x", padx=5, pady=3)
        
        display_frame = tk.Frame(pos_frame, bg="#2c3e50", padx=5, pady=4)
        display_frame.pack(fill="x", padx=3, pady=3)
        
        self.pos_x_var = tk.StringVar(value="---")
        self.pos_y_var = tk.StringVar(value="---")
        self.pos_z_var = tk.StringVar(value="---")
        
        for i, (label, var, color) in enumerate([
            ("X:", self.pos_x_var, "#3498db"),
            ("Y:", self.pos_y_var, "#2ecc71"),
            ("Z:", self.pos_z_var, "#e74c3c")
        ]):
            tk.Label(display_frame, text=label, font=("Arial", 8), bg="#2c3e50", fg="#ecf0f1").grid(
                row=i, column=0, sticky="e")
            tk.Label(display_frame, textvariable=var, font=("Courier", 9), bg="#2c3e50",
                    fg=color, width=8).grid(row=i, column=1, padx=2)
        
        btn_frame = tk.Frame(pos_frame)
        btn_frame.pack(fill="x", padx=3, pady=2)
        
        self.start_monitor_btn = ttk.Button(btn_frame, text="▶", command=self.start_monitor, width=3)
        self.start_monitor_btn.pack(side="left", padx=1)
        
        self.stop_monitor_btn = ttk.Button(btn_frame, text="⏸", command=self.stop_monitor,
                                          state="disabled", width=3)
        self.stop_monitor_btn.pack(side="left", padx=1)

    def _build_debug_panel(self, parent):
        """Build debug mode panel."""
        debug_frame = ttk.LabelFrame(parent, text="🐛 Debug")
        debug_frame.pack(fill="x", padx=5, pady=3)
        
        mode_frame = tk.Frame(debug_frame)
        mode_frame.pack(fill="x", padx=3, pady=2)
        
        tk.Radiobutton(mode_frame, text="Normal", variable=self.execution_mode,
                      value="normal", font=("Arial", 7)).pack(side="left", padx=2)
        tk.Radiobutton(mode_frame, text="Step-by-Step", variable=self.execution_mode,
                      value="step", font=("Arial", 7)).pack(side="left", padx=2)
        
        self.debug_step_var = tk.StringVar(value="- / -")
        self.debug_status_var = tk.StringVar(value="Ready")
        
        tk.Label(debug_frame, textvariable=self.debug_step_var, font=("Arial", 8, "bold")).pack()
        tk.Label(debug_frame, textvariable=self.debug_status_var, font=("Arial", 7),
                fg="#7f8c8d").pack()
        
        debug_btns = tk.Frame(debug_frame)
        debug_btns.pack(fill="x", padx=3, pady=2)
        
        self.next_step_btn = ttk.Button(debug_btns, text="▶ Next", command=self.execute_next_step,
                                       state="disabled")
        self.next_step_btn.pack(side="left", padx=1, fill="x", expand=True)
        
        self.stop_debug_btn = ttk.Button(debug_btns, text="⏹", command=self.stop_debug_execution,
                                        state="disabled", width=3)
        self.stop_debug_btn.pack(side="left", padx=1)
    def _build_step_editor_panel(self, parent):
        """Build step editor panel."""
        editor = ttk.LabelFrame(parent, text="Step Editor")
        editor.pack(fill="x", padx=5, pady=3)

        self.cmd_var = tk.StringVar(value="G01")
        self.x_var = tk.StringVar()
        self.y_var = tk.StringVar()
        self.z_var = tk.StringVar()
        self.f_var = tk.StringVar()
        self.delay_var = tk.StringVar()
        self.do0_var = tk.StringVar()

        tk.Label(editor, text="Cmd:", font=("Arial", 8)).grid(row=0, column=0, sticky="e", padx=2, pady=1)
        ttk.Combobox(editor, textvariable=self.cmd_var, values=("G00", "G01"), 
                     width=10, font=("Arial", 8)).grid(row=0, column=1, sticky="ew", padx=2, pady=1)

        tk.Label(editor, text="X:", font=("Arial", 8)).grid(row=1, column=0, sticky="e", padx=2, pady=1)
        ttk.Entry(editor, textvariable=self.x_var, width=12, font=("Arial", 8)).grid(
            row=1, column=1, sticky="ew", padx=2, pady=1)

        tk.Label(editor, text="Y:", font=("Arial", 8)).grid(row=2, column=0, sticky="e", padx=2, pady=1)
        ttk.Entry(editor, textvariable=self.y_var, width=12, font=("Arial", 8)).grid(
            row=2, column=1, sticky="ew", padx=2, pady=1)

        tk.Label(editor, text="Z:", font=("Arial", 8)).grid(row=3, column=0, sticky="e", padx=2, pady=1)
        ttk.Entry(editor, textvariable=self.z_var, width=12, font=("Arial", 8)).grid(
            row=3, column=1, sticky="ew", padx=2, pady=1)

        tk.Label(editor, text="F:", font=("Arial", 8)).grid(row=4, column=0, sticky="e", padx=2, pady=1)
        ttk.Entry(editor, textvariable=self.f_var, width=12, font=("Arial", 8)).grid(
            row=4, column=1, sticky="ew", padx=2, pady=1)

        tk.Label(editor, text="Delay:", font=("Arial", 8)).grid(row=5, column=0, sticky="e", padx=2, pady=1)
        ttk.Entry(editor, textvariable=self.delay_var, width=12, font=("Arial", 8)).grid(
            row=5, column=1, sticky="ew", padx=2, pady=1)

        tk.Label(editor, text="DO0:", font=("Arial", 8)).grid(row=6, column=0, sticky="e", padx=2, pady=1)
        ttk.Entry(editor, textvariable=self.do0_var, width=12, font=("Arial", 8)).grid(
            row=6, column=1, sticky="ew", padx=2, pady=1)

        editor.columnconfigure(1, weight=1)

        btn_frame1 = tk.Frame(editor)
        btn_frame1.grid(row=7, column=0, columnspan=2, pady=3, sticky="ew", padx=2)

        for i, (text, cmd) in enumerate([("Add", self.on_add_step), 
                                         ("Insert", self.on_insert_step),
                                         ("Update", self.on_update_step), 
                                         ("Del", self.on_delete_step)]):
            ttk.Button(btn_frame1, text=text, command=cmd).grid(row=0, column=i, padx=1, sticky="ew")
            btn_frame1.columnconfigure(i, weight=1)

        btn_frame2 = tk.Frame(editor)
        btn_frame2.grid(row=8, column=0, columnspan=2, pady=3, sticky="ew", padx=2)

        self.copy_btn = ttk.Button(btn_frame2, text="📋 Copy", command=self.on_copy_step)
        self.copy_btn.grid(row=0, column=0, padx=1, sticky="ew")

        self.paste_btn = ttk.Button(btn_frame2, text="📄 Paste", command=self.on_paste_step, state="disabled")
        self.paste_btn.grid(row=0, column=1, padx=1, sticky="ew")

        self.duplicate_btn = ttk.Button(btn_frame2, text="⎘ Dup", command=self.on_duplicate_step)
        self.duplicate_btn.grid(row=0, column=2, padx=1, sticky="ew")

        btn_frame2.columnconfigure(0, weight=1)
        btn_frame2.columnconfigure(1, weight=1)
        btn_frame2.columnconfigure(2, weight=1)

        btn_frame3 = tk.Frame(editor)
        btn_frame3.grid(row=9, column=0, columnspan=2, pady=3, sticky="ew", padx=2)

        self.move_up_btn = ttk.Button(btn_frame3, text="⬆ Up", command=self.on_move_up)
        self.move_up_btn.grid(row=0, column=0, padx=1, sticky="ew")

        self.move_down_btn = ttk.Button(btn_frame3, text="⬇ Down", command=self.on_move_down)
        self.move_down_btn.grid(row=0, column=1, padx=1, sticky="ew")

        self.jog_btn = ttk.Button(btn_frame3, text="🕹️ Jog", command=self.open_jog_control)
        self.jog_btn.grid(row=0, column=2, padx=1, sticky="ew")

        btn_frame3.columnconfigure(0, weight=1)
        btn_frame3.columnconfigure(1, weight=1)
        btn_frame3.columnconfigure(2, weight=1)

        self.clipboard_label = tk.Label(
            editor, 
            text="Clipboard: Empty", 
            font=("Arial", 7), 
            fg="#95a5a6",
            wraplength=200,
            justify="left"
        )
        self.clipboard_label.grid(row=10, column=0, columnspan=2, pady=2, sticky="w", padx=5)

    def _build_program_panel(self, parent):
        """Build program management panel."""
        prog_frame = ttk.LabelFrame(parent, text="Program")
        prog_frame.pack(fill="x", padx=5, pady=3)
        
        prog_btns1 = tk.Frame(prog_frame)
        prog_btns1.pack(fill="x", padx=3, pady=2)
        
        for i, (text, cmd) in enumerate([("New", self.on_new_program), 
                                         ("Open", self.on_open_program),
                                         ("Save", self.on_save_program)]):
            ttk.Button(prog_btns1, text=text, command=cmd).grid(row=0, column=i, padx=1, sticky="ew")
            prog_btns1.columnconfigure(i, weight=1)

        prog_btns2 = tk.Frame(prog_frame)
        prog_btns2.pack(fill="x", padx=3, pady=2)

        ttk.Button(prog_btns2, text="Select All", command=self.on_select_all).grid(
            row=0, column=0, padx=1, sticky="ew")
        ttk.Button(prog_btns2, text="Clear All", command=self.on_clear_all).grid(
            row=0, column=1, padx=1, sticky="ew")

        prog_btns2.columnconfigure(0, weight=1)
        prog_btns2.columnconfigure(1, weight=1)

        self.step_count_label = tk.Label(
            prog_frame,
            text="Total: 0 steps",
            font=("Arial", 7),
            fg="#7f8c8d"
        )
        self.step_count_label.pack(padx=3, pady=2)

    def _build_run_panel(self, parent):
        """Build run control panel."""
        run_frame = ttk.LabelFrame(parent, text="Run")
        run_frame.pack(fill="x", padx=5, pady=3)

        self.run_btn = ttk.Button(run_frame, text="▶ Run Program", command=self.on_run_program)
        self.run_btn.pack(fill="x", padx=3, pady=2)

        self.status_var = tk.StringVar(value="Ready")
        tk.Label(run_frame, textvariable=self.status_var, font=("Arial", 7),
                wraplength=250, fg="#7f8c8d").pack(padx=3, pady=2)
    # ---------- NEW: Order Queue Methods ----------
    
    def update_order_estimate(self):
        """Update estimated time for current order configuration."""
        if not self.program.steps:
            self.order_est_var.set("Est: No program loaded")
            return
        
        single_time = estimate_program_time(self.program)
        quantity = self.quantity_var.get()
        total_time = single_time * quantity
        
        self.order_est_var.set(f"Est: {format_time(total_time)} ({format_time(single_time)} per juice)")
    
    def on_add_to_queue(self):
        """Add new order to queue."""
        if not self.program.steps:
            messagebox.showwarning("No Program", "Load a program first!")
            return
        
        flavor = self.flavor_var.get()
        quantity = self.quantity_var.get()
        
        # Create copy of current program for this order
        order_program = Program(f"{flavor}_order")
        order_program.steps = [Step(cmd=s.cmd, x=s.x, y=s.y, z=s.z, f=s.f, 
                                    delay=s.delay, do0=s.do0) 
                               for s in self.program.steps]
        
        order = self.order_queue.add_order(flavor, quantity, order_program)
        
        self.refresh_queue_display()
        self.status_var.set(f"✓ Added {order} to queue")
        
        # Auto-calculate total queue time
        self.update_total_queue_time()
    
    def refresh_queue_display(self):
        """Refresh the queue listbox display."""
        self.queue_listbox.delete(0, tk.END)
        
        for order in self.order_queue.orders:
            status_symbol = "🔄" if order.status == "Processing" else "⏳" if order.status == "Pending" else "✓"
            display_text = f"{status_symbol} {order} - {order.status}"
            self.queue_listbox.insert(tk.END, display_text)
            
            # Highlight current order
            if order.status == "Processing":
                self.queue_listbox.itemconfig(tk.END, bg="#d5f4e6", fg="#000000")
        
        # Update count
        count = self.order_queue.get_total_count()
        self.queue_count_var.set(f"Queue ({count} order{'s' if count != 1 else ''}):")
    
    def update_total_queue_time(self):
        """Calculate and display total queue time."""
        total_time = 0.0
        for order in self.order_queue.orders:
            if order.status != "Completed":
                single_time = estimate_program_time(order.program)
                total_time += single_time * order.quantity
        
        self.total_queue_time_var.set(f"Total Queue Time: {format_time(total_time)}")
    
    def on_start_queue(self):
        """Start processing the order queue."""
        if self.order_queue.get_total_count() == 0:
            messagebox.showinfo("Empty Queue", "Add orders to queue first!")
            return
        
        if self.queue_processing:
            messagebox.showinfo("Already Running", "Queue is already processing!")
            return
        
        # Check E-stop
        estop_result = check_emergency_stop()
        if estop_result['is_pressed'] is True:
            messagebox.showerror("E-Stop Active", "Release E-stop first!")
            return
        
        self.queue_processing = True
        self.start_queue_btn.config(state="disabled")
        self.stop_queue_btn.config(state="normal")
        self.add_queue_btn.config(state="disabled")  # Lock during processing
        
        # Start queue processor in thread
        self.queue_thread = threading.Thread(target=self.process_queue, daemon=True)
        self.queue_thread.start()
    
    def on_stop_queue(self):
        """Stop queue processing."""
        self.queue_processing = False
        self.start_queue_btn.config(state="normal")
        self.stop_queue_btn.config(state="disabled")
        self.add_queue_btn.config(state="normal")
        self.status_var.set("Queue stopped")
    
    def on_clear_queue(self):
        """Clear all orders from queue."""
        if self.queue_processing:
            messagebox.showwarning("Queue Active", "Stop queue before clearing!")
            return
        
        if self.order_queue.get_total_count() == 0:
            return
        
        response = messagebox.askyesno("Clear Queue", 
                                       f"Clear all {self.order_queue.get_total_count()} orders?")
        if response:
            self.order_queue.clear_all()
            self.refresh_queue_display()
            self.update_total_queue_time()
            self.status_var.set("Queue cleared")
    
    def process_queue(self):
        """Process orders in FIFO order (runs in separate thread)."""
        while self.queue_processing:
            # Get next pending order
            order = self.order_queue.get_next_pending()
            
            if order is None:
                # No more orders
                self.queue_processing = False
                self.after(0, lambda: self.start_queue_btn.config(state="normal"))
                self.after(0, lambda: self.stop_queue_btn.config(state="disabled"))
                self.after(0, lambda: self.add_queue_btn.config(state="normal"))
                self.after(0, lambda: self.status_var.set("✓ Queue complete!"))
                self.after(0, lambda: messagebox.showinfo("Queue Complete", 
                                                          "All orders processed!"))
                break
            
            # Mark as processing
            order.status = "Processing"
            self.after(0, self.refresh_queue_display)
            
            # Process each juice in the order
            for juice_num in range(1, order.quantity + 1):
                if not self.queue_processing:
                    break
                
                self.current_order_juice = juice_num
                
                # Update UI
                self.after(0, lambda o=order, j=juice_num: 
                          self.current_order_var.set(f"Current: {o} ({j}/{o.quantity})"))
                
                # Calculate progress (thread-safe)
                with self.program_lock:
                    total_steps = len(order.program.steps)
                
                try:
                    # Execute program with progress tracking (thread-safe)
                    with self.program_lock:
                        steps_list = list(order.program.steps)
                    
                    for step_idx, step in enumerate(steps_list):
                        if not self.queue_processing:
                            break
                        
                        # Update progress
                        progress = ((juice_num - 1) * total_steps + step_idx + 1) / (order.quantity * total_steps) * 100
                        self.after(0, lambda p=progress: self.progress_var.set(p))
                        self.after(0, lambda p=progress: self.progress_text_var.set(f"Progress: {p:.0f}%"))
                        
                        # Simulate execution with delay (replace with actual run_program later)
                        time.sleep(step.delay)
                        
                        # Estimate time remaining
                        remaining_steps = (order.quantity - juice_num) * total_steps + (total_steps - step_idx - 1)
                        avg_step_time = estimate_program_time(order.program) / total_steps
                        remaining_time = remaining_steps * avg_step_time
                        self.after(0, lambda t=remaining_time: 
                                  self.time_remaining_var.set(f"Time Remaining: {format_time(t)}"))
                
                except Exception as e:
                    self.after(0, lambda err=str(e): messagebox.showerror("Execution Error", err))
                    self.queue_processing = False
                    break
            
            # Mark order as completed
            if self.queue_processing:
                order.status = "Completed"
                self.after(0, self.refresh_queue_display)
                self.after(0, self.update_total_queue_time)
        
        # Reset progress
        self.after(0, lambda: self.progress_var.set(0))
        self.after(0, lambda: self.current_order_var.set("Current: None"))
    # ---------- Speed Override Methods (Upgrade #4) ----------
    
    def set_speed_preset(self, percent):
        if percent > 100:
            response = messagebox.askyesno("High Speed", f"Set {percent}%?\nEnsure safety!")
            if not response:
                return
        self.speed_override.set(percent)
        self.update_speed_info()
    
    def on_speed_change(self, value):
        self.update_speed_info()
    
    def update_speed_info(self):
        override = self.speed_override.get() / 100.0
        self.speed_info.config(text=f"F20 → F{20*override:.1f} ({self.speed_override.get():.0f}%)")
    
    def get_speed_multiplier(self):
        return self.speed_override.get() / 100.0

    # ---------- Debug Mode Methods (Upgrade #3) ----------
    
    def start_step_execution(self):
        if not self.program.steps:
            messagebox.showinfo("Debug", "Program empty")
            return
        try:
            self.step_executor = StepExecutor(self.program)
            self.step_executor.speed_override = self.get_speed_multiplier()
            self.step_executor.start()
            self.debug_running = True
            self.next_step_btn.config(state="normal")
            self.stop_debug_btn.config(state="normal")
            self.run_btn.config(state="disabled")
            self.debug_step_var.set(f"0 / {len(self.program.steps)}")
            self.highlight_tree_row(0)
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def execute_next_step(self):
        if not self.step_executor:
            return
        try:
            self.step_executor.speed_override = self.get_speed_multiplier()
            result = self.step_executor.execute_next_step()
            self.debug_step_var.set(f"{result['step_index'] + 1} / {result['total_steps']}")
            self.debug_status_var.set(result['status'][:20])
            self.highlight_tree_row(result['step_index'])
            if result['completed']:
                self.stop_debug_execution()
                messagebox.showinfo("Done", "Complete!")
            if result['error']:
                messagebox.showerror("Error", result['error'])
                self.stop_debug_execution()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.stop_debug_execution()
    
    def stop_debug_execution(self):
        if self.step_executor:
            self.step_executor.stop()
            self.step_executor = None
        self.debug_running = False
        self.next_step_btn.config(state="disabled")
        self.stop_debug_btn.config(state="disabled")
        self.run_btn.config(state="normal")
        self.clear_tree_highlight()
    
    def highlight_tree_row(self, index):
        self.clear_tree_highlight()
        if 0 <= index < len(self.program.steps):
            self.tree.selection_set(str(index))
            self.tree.see(str(index))
            self.tree.item(str(index), tags=('current',))
            self.tree.tag_configure('current', background='#3498db', foreground='white')
    
    def clear_tree_highlight(self):
        for item in self.tree.get_children():
            self.tree.item(item, tags=())

    # ---------- E-Stop Methods (Upgrade #2) ----------
    
    def check_estop_status(self):
        try:
            result = check_emergency_stop()
            if result['is_pressed'] is None:
                self.estop_icon.config(fg="orange")
                self.estop_status_text.config(text="Unknown")
                self.stop_estop_blink()
            elif result['is_pressed']:
                self.estop_status_text.config(text="ACTIVE!", fg="#e74c3c")
                self.start_estop_blink()
                self.bell()
            else:
                self.estop_icon.config(fg="#2ecc71")
                self.estop_status_text.config(text="Normal", fg="#2ecc71")
                self.stop_estop_blink()
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def start_estop_blink(self):
        self.estop_blink_state = not self.estop_blink_state
        self.estop_icon.config(fg="#e74c3c" if self.estop_blink_state else "#34495e")
        self.estop_blink_job = self.after(500, self.start_estop_blink)
    
    def stop_estop_blink(self):
        if self.estop_blink_job:
            self.after_cancel(self.estop_blink_job)
            self.estop_blink_job = None

    # ---------- Position Monitoring (Upgrade #1) ----------
    
    def start_monitor(self):
        self.monitor_active = True
        self.start_monitor_btn.config(state="disabled")
        self.stop_monitor_btn.config(state="normal")
        self.update_position()
    
    def stop_monitor(self):
        self.monitor_active = False
        self.start_monitor_btn.config(state="normal")
        self.stop_monitor_btn.config(state="disabled")
        if self.monitor_job:
            self.after_cancel(self.monitor_job)
            self.monitor_job = None
    
    def update_position(self):
        if not self.monitor_active:
            return
        try:
            pos_data = query_position()
            if pos_data['x'] is not None:
                self.pos_x_var.set(f"{pos_data['x']:.1f}")
                self.pos_y_var.set(f"{pos_data['y']:.1f}")
                self.pos_z_var.set(f"{pos_data['z']:.1f}")
            else:
                self.pos_x_var.set("---")
                self.pos_y_var.set("---")
                self.pos_z_var.set("---")
        except:
            pass
        self.monitor_job = self.after(500, self.update_position)
    # ---------- Copy/Paste/Duplicate Methods (Upgrade #5) ----------
    
    def on_copy_step(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Copy", "Select a step to copy first")
            return
        
        index = int(sel[0])
        step = self.program.steps[index]
        
        self.clipboard_step = Step(
            cmd=step.cmd, x=step.x, y=step.y, z=step.z,
            f=step.f, delay=step.delay, do0=step.do0
        )
        
        self.paste_btn.config(state="normal")
        clipboard_text = f"Clipboard: {step.cmd}"
        if step.x is not None:
            clipboard_text += f" X:{step.x}"
        if step.y is not None:
            clipboard_text += f" Y:{step.y}"
        if step.z is not None:
            clipboard_text += f" Z:{step.z}"
        
        self.clipboard_label.config(text=clipboard_text, fg="#2ecc71")
        self.status_var.set(f"✓ Copied step {index + 1}")
    
    def on_paste_step(self):
        if self.clipboard_step is None:
            messagebox.showinfo("Paste", "Clipboard empty. Copy a step first.")
            return
        
        new_step = Step(
            cmd=self.clipboard_step.cmd, x=self.clipboard_step.x, 
            y=self.clipboard_step.y, z=self.clipboard_step.z,
            f=self.clipboard_step.f, delay=self.clipboard_step.delay, 
            do0=self.clipboard_step.do0
        )
        
        sel = self.tree.selection()
        if sel:
            index = int(sel[0]) + 1
        else:
            index = len(self.program.steps)
        
        self.program.steps.insert(index, new_step)
        self._refresh_tree()
        
        self.tree.selection_set(str(index))
        self.tree.see(str(index))
        self.status_var.set(f"✓ Pasted at {index + 1}")
    
    def on_duplicate_step(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Duplicate", "Select a step first")
            return
        
        index = int(sel[0])
        step = self.program.steps[index]
        
        new_step = Step(
            cmd=step.cmd, x=step.x, y=step.y, z=step.z,
            f=step.f, delay=step.delay, do0=step.do0
        )
        
        self.program.steps.insert(index + 1, new_step)
        self._refresh_tree()
        
        self.tree.selection_set(str(index + 1))
        self.tree.see(str(index + 1))
        self.status_var.set(f"✓ Duplicated step {index + 1}")

    # ---------- Move Up/Down Methods (Upgrade #6) ----------
    
    def on_move_up(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Move Up", "Select a step to move")
            return
        
        index = int(sel[0])
        
        if index == 0:
            self.status_var.set("Already at top")
            return
        
        self.program.steps[index], self.program.steps[index - 1] = \
            self.program.steps[index - 1], self.program.steps[index]
        
        self._refresh_tree()
        self.tree.selection_set(str(index - 1))
        self.tree.see(str(index - 1))
        
        self.status_var.set(f"✓ Moved step {index + 1} → {index}")
    
    def on_move_down(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Move Down", "Select a step to move")
            return
        
        index = int(sel[0])
        
        if index >= len(self.program.steps) - 1:
            self.status_var.set("Already at bottom")
            return
        
        self.program.steps[index], self.program.steps[index + 1] = \
            self.program.steps[index + 1], self.program.steps[index]
        
        self._refresh_tree()
        self.tree.selection_set(str(index + 1))
        self.tree.see(str(index + 1))
        
        self.status_var.set(f"✓ Moved step {index + 1} → {index + 2}")

    def open_jog_control(self):
        """Open the jog control window for manual arm movement."""
        try:
            JogControlWindow(self.master, program=self.program)
        except Exception as e:
            messagebox.showerror("Jog Control Error", f"Failed to open jog control: {str(e)}")

    # ---------- Select All & Clear All Methods (Upgrade #7) ----------
    
    def on_select_all(self):
        if not self.program.steps:
            self.status_var.set("No steps to select")
            return
        
        all_items = self.tree.get_children()
        self.tree.selection_set(all_items)
        
        self.status_var.set(f"✓ Selected all {len(self.program.steps)} steps")
    
    def on_clear_all(self):
        if not self.program.steps:
            messagebox.showinfo("Clear All", "Program is already empty")
            return
        
        count = len(self.program.steps)
        response = messagebox.askyesno(
            "Clear All Steps",
            f"Delete all {count} steps?\n\nThis cannot be undone!",
            icon='warning'
        )
        
        if response:
            self.program.steps.clear()
            self._refresh_tree()
            self.status_var.set(f"✓ Cleared {count} steps")
        else:
            self.status_var.set("Cancelled")
    # ---------- Helper Methods ----------

    def _read_step_from_fields(self) -> Optional[Step]:
        try:
            cmd = self.cmd_var.get().strip() or "G01"
            if cmd not in ("G00", "G01"):
                raise ValueError("Cmd must be G00 or G01")
            
            def parse_float(s):
                s = s.strip()
                return float(s) if s else None
            
            return Step(
                cmd=cmd,
                x=parse_float(self.x_var.get()),
                y=parse_float(self.y_var.get()),
                z=parse_float(self.z_var.get()),
                f=float(self.f_var.get()) if self.f_var.get().strip() else 20.0,
                delay=float(self.delay_var.get()) if self.delay_var.get().strip() else 0.5,
                do0=parse_float(self.do0_var.get()),
            )
        except ValueError as e:
            messagebox.showerror("Invalid", str(e))
            return None

    def _refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for idx, s in enumerate(self.program.steps):
            self.tree.insert("", "end", iid=str(idx),
                values=(s.cmd, s.x, s.y, s.z, s.f, s.delay, s.do0))
        
        count = len(self.program.steps)
        self.step_count_label.config(text=f"Total: {count} step{'s' if count != 1 else ''}")
        
        # Update order estimate when program changes
        self.update_order_estimate()

    # ---------- Step Editor Callbacks ----------

    def on_add_step(self):
        step = self._read_step_from_fields()
        if step:
            self.program.steps.append(step)
            self._refresh_tree()

    def on_insert_step(self):
        step = self._read_step_from_fields()
        if not step:
            return
        sel = self.tree.selection()
        index = int(sel[0]) if sel else len(self.program.steps)
        self.program.steps.insert(index, step)
        self._refresh_tree()

    def on_update_step(self):
        step = self._read_step_from_fields()
        if not step:
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Update", "Select step first")
            return
        self.program.steps[int(sel[0])] = step
        self._refresh_tree()

    def on_delete_step(self):
        sel = self.tree.selection()
        if sel:
            del self.program.steps[int(sel[0])]
            self._refresh_tree()

    def on_select_step(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        s = self.program.steps[int(sel[0])]
        self.cmd_var.set(s.cmd)
        self.x_var.set("" if s.x is None else str(s.x))
        self.y_var.set("" if s.y is None else str(s.y))
        self.z_var.set("" if s.z is None else str(s.z))
        self.f_var.set(str(s.f))
        self.delay_var.set(str(s.delay))
        self.do0_var.set("" if s.do0 is None else str(s.do0))

    # ---------- Program Management Callbacks ----------

    def on_new_program(self):
        self.program = Program("unnamed")
        self.current_path = None
        self._refresh_tree()
        self.status_var.set("New program")

    def on_open_program(self):
        os.makedirs(PROGRAMS_DIR, exist_ok=True)
        path = filedialog.askopenfilename(initialdir=PROGRAMS_DIR,
            filetypes=[("JSON", "*.json"), ("All", "*.*")])
        if not path:
            return
        try:
            self.program = Program.load(path)
            self.current_path = path
            self._refresh_tree()
            self.status_var.set(f"Loaded: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Open failed", str(e))

    def on_save_program(self):
        if not self.current_path:
            os.makedirs(PROGRAMS_DIR, exist_ok=True)
            path = filedialog.asksaveasfilename(initialdir=PROGRAMS_DIR,
                defaultextension=".json", filetypes=[("JSON", "*.json")])
            if not path:
                return
            self.current_path = path
        try:
            self.program.save(self.current_path)
            self.status_var.set(f"Saved: {os.path.basename(self.current_path)}")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    def on_run_program(self):
        if not self.program.steps:
            messagebox.showinfo("Run", "Program empty")
            return
        
        if self.execution_mode.get() == "step":
            self.start_step_execution()
            return
        
        estop_result = check_emergency_stop()
        if estop_result['is_pressed'] is True:
            messagebox.showerror("E-Stop", "Release E-stop first")
            return
        
        try:
            was_monitoring = self.monitor_active
            if was_monitoring:
                self.stop_monitor()
            
            speed_mult = self.get_speed_multiplier()
            self.status_var.set(f"Running at {self.speed_override.get():.0f}%...")
            self.master.update_idletasks()
            
            run_program(self.program, speed_mult)
            self.status_var.set("Finished")
            
            if was_monitoring:
                self.start_monitor()
        except Exception as e:
            messagebox.showerror("Run failed", str(e))
            self.status_var.set("Error")


def main(root=None):
    if root is None:
        root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
