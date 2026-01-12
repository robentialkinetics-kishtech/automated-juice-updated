# app.py
#
# Customer kiosk: owner login → customer ordering → developer settings.

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

from drink_runner import make_drink
import gui  # teaching GUI

OWNER_PASSWORD = "0000"
DEV_PASSWORD = "0000"

DRINKS = [
    ("mango", "Mango Juice"),      
    ("orange", "Orange Juice"),
    ("grape", "Grape Juice"),
    ("apple", "Apple Juice"),
]

# Estimated time per drink in seconds (adjust based on your actual times)
DRINK_TIME_ESTIMATE = {
    "mango": 45,
    "orange": 40,
    "grape": 50,
    "apple": 42,
}
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ZKBot Juice Kiosk")
        self.geometry("900x550")

        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self.frame = None
        self.show_owner_login()

    def show_frame(self, frame_cls, *args):
        if self.frame is not None:
            self.frame.destroy()
        self.frame = frame_cls(self.container, *args)
        self.frame.pack(fill="both", expand=True)

    def show_owner_login(self):
        self.show_frame(OwnerLogin, self.show_customer)

    def show_customer(self):
        self.show_frame(CustomerScreen, self.show_dev_login)

    def show_dev_login(self):
        self.show_frame(DevLogin, self.show_dev_screen, self.show_customer)

    def show_dev_screen(self):
        self.show_frame(DeveloperScreen, self.show_customer)


class OwnerLogin(tk.Frame):
    def __init__(self, master, on_success):
        super().__init__(master)
        self.on_success = on_success

        tk.Label(self, text="ZKBot Juice Station", font=("Arial", 22, "bold")).pack(pady=20)
        tk.Label(self, text="Owner Password").pack(pady=(10, 5))

        self.entry = tk.Entry(self, show="*")
        self.entry.pack()
        self.entry.focus_set()

        tk.Button(self, text="Login", width=18, command=self.login).pack(pady=15)

    def login(self):
        if self.entry.get() == OWNER_PASSWORD:
            self.on_success()
        else:
            messagebox.showerror("Access denied", "Wrong password")
            self.entry.delete(0, tk.END)


class DevLogin(tk.Frame):
    def __init__(self, master, on_success, on_back):
        super().__init__(master)
        self.on_success = on_success
        self.on_back = on_back

        tk.Label(self, text="Developer Login", font=("Arial", 20, "bold")).pack(pady=20)
        tk.Label(self, text="Developer Password").pack(pady=(10, 5))

        self.entry = tk.Entry(self, show="*")
        self.entry.pack()
        self.entry.focus_set()

        row = tk.Frame(self)
        row.pack(pady=15)

        tk.Button(row, text="Back", width=10, command=self.on_back).pack(side="left", padx=5)
        tk.Button(row, text="Login", width=10, command=self.login).pack(side="left", padx=5)

    def login(self):
        if self.entry.get() == DEV_PASSWORD:
            self.on_success()
        else:
            messagebox.showerror("Access denied", "Wrong developer password")
            self.entry.delete(0, tk.END)
class CustomerScreen(tk.Frame):
    def __init__(self, master, on_open_dev):
        super().__init__(master)
        self.on_open_dev = on_open_dev
        self.order_queue = []  # List of (drink_key, quantity) tuples
        self.running = False
        self.current_order_index = 0
        self.current_drink_in_order = 0

        # Top bar
        top = tk.Frame(self)
        top.pack(fill="x", pady=5)

        tk.Label(top, text="Customer Order", font=("Arial", 16, "bold")).pack(side="left", padx=10)
        tk.Button(top, text="Developer / Settings", command=self.on_open_dev).pack(side="right", padx=10)

        # Layout
        body = tk.Frame(self)
        body.pack(fill="both", expand=True, padx=10, pady=10)

        left = tk.Frame(body)
        left.pack(side="left", fill="both", expand=True)

        right = tk.Frame(body, bd=2, relief="solid", bg="#f0f0f0")
        right.pack(side="right", fill="y", padx=(10, 0))

        # Left side: Drink selection with quantity
        tk.Label(left, text="Select Drinks", font=("Arial", 14, "bold")).pack(pady=5)

        grid = tk.Frame(left)
        grid.pack(pady=10)

        self.quantity_vars = {}
        
        for i, (key, label) in enumerate(DRINKS):
            frame = tk.Frame(grid, bd=1, relief="solid", padx=10, pady=10)
            frame.grid(row=i // 2, column=i % 2, padx=8, pady=8, sticky="nsew")
            
            tk.Label(frame, text=label, font=("Arial", 11, "bold")).pack()
            
            qty_frame = tk.Frame(frame)
            qty_frame.pack(pady=5)
            
            tk.Label(qty_frame, text="Qty:").pack(side="left", padx=2)
            
            self.quantity_vars[key] = tk.IntVar(value=1)
            qty_spin = tk.Spinbox(qty_frame, from_=1, to=10, width=5, 
                                 textvariable=self.quantity_vars[key])
            qty_spin.pack(side="left", padx=2)
            
            tk.Button(frame, text=f"Add to Queue", 
                     command=lambda k=key: self.add_to_queue(k)).pack(pady=5)

        # Right side: Order Queue
        tk.Label(right, text="Order Queue", font=("Arial", 14, "bold"), 
                bg="#f0f0f0").pack(pady=10)
        
        # Queue display
        queue_frame = tk.Frame(right, bg="#ffffff", bd=1, relief="sunken")
        queue_frame.pack(padx=10, pady=5, fill="both", expand=True)
        
        self.queue_listbox = tk.Listbox(queue_frame, width=28, height=8, 
                                        font=("Arial", 9))
        self.queue_listbox.pack(fill="both", expand=True, padx=2, pady=2)
        
        self.queue_count_label = tk.Label(right, text="Queue: 0 orders", 
                                          font=("Arial", 9), bg="#f0f0f0")
        self.queue_count_label.pack(pady=2)

        # Progress section
        progress_frame = tk.Frame(right, bg="#e8f4f8", bd=1, relief="solid")
        progress_frame.pack(padx=10, pady=10, fill="x")
        
        tk.Label(progress_frame, text="Progress", font=("Arial", 10, "bold"),
                bg="#e8f4f8").pack(pady=5)
        
        self.current_label = tk.Label(progress_frame, text="Current: None",
                                      font=("Arial", 9), bg="#e8f4f8")
        self.current_label.pack(pady=2)
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                           maximum=100, length=200)
        self.progress_bar.pack(pady=5, padx=10, fill="x")
        
        self.progress_text = tk.Label(progress_frame, text="0%", 
                                      font=("Arial", 8), bg="#e8f4f8")
        self.progress_text.pack(pady=2)
        
        self.time_remaining_label = tk.Label(progress_frame, text="Time: --",
                                            font=("Arial", 8), bg="#e8f4f8")
        self.time_remaining_label.pack(pady=2)
        
        self.total_time_label = tk.Label(progress_frame, text="Total Queue: 0m 0s",
                                         font=("Arial", 8), bg="#e8f4f8")
        self.total_time_label.pack(pady=2)

        # Control buttons
        btn_row = tk.Frame(right, bg="#f0f0f0")
        btn_row.pack(pady=10)

        self.clear_btn = tk.Button(btn_row, text="Clear", width=10, command=self.clear_queue)
        self.clear_btn.pack(side="left", padx=5)
        
        self.start_btn = tk.Button(btn_row, text="Start", width=10, 
                                   command=self.start_queue, bg="#2ecc71", fg="white")
        self.start_btn.pack(side="left", padx=5)

        self.status = tk.StringVar(value="Idle")
        tk.Label(right, textvariable=self.status, fg="green", 
                wraplength=220, bg="#f0f0f0", font=("Arial", 9)).pack(pady=5)

    def add_to_queue(self, juice_key):
        """Add drink to queue with quantity."""
        if self.running:
            messagebox.showwarning("Processing", "Wait for current queue to finish!")
            return
        
        quantity = self.quantity_vars[juice_key].get()
        drink_name = next((lbl for k, lbl in DRINKS if k == juice_key), juice_key)
        
        self.order_queue.append((juice_key, quantity))
        self.refresh_queue_display()
        self.update_total_time()
        
        self.status.set(f"✓ Added {quantity}x {drink_name}")

    def refresh_queue_display(self):
        """Refresh the queue listbox."""
        self.queue_listbox.delete(0, tk.END)
        
        for idx, (key, qty) in enumerate(self.order_queue, start=1):
            drink_name = next((lbl for k, lbl in DRINKS if k == key), key)
            status = "🔄" if idx - 1 == self.current_order_index and self.running else "⏳"
            display_text = f"{status} #{idx}: {drink_name} x{qty}"
            self.queue_listbox.insert(tk.END, display_text)
            
            # Highlight current order
            if idx - 1 == self.current_order_index and self.running:
                self.queue_listbox.itemconfig(tk.END, bg="#d5f4e6")
        
        count = len(self.order_queue)
        self.queue_count_label.config(text=f"Queue: {count} order{'s' if count != 1 else ''}")

    def update_total_time(self):
        """Calculate and display total queue time."""
        total_seconds = 0
        for key, qty in self.order_queue:
            drink_time = DRINK_TIME_ESTIMATE.get(key, 45)
            total_seconds += drink_time * qty
        
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        self.total_time_label.config(text=f"Total Queue: {minutes}m {seconds}s")

    def clear_queue(self):
        """Clear all orders from queue."""
        if self.running:
            messagebox.showwarning("Processing", "Cannot clear during processing!")
            return
        
        if not self.order_queue:
            return
        
        response = messagebox.askyesno("Clear Queue", 
                                       f"Clear all {len(self.order_queue)} orders?")
        if response:
            self.order_queue.clear()
            self.refresh_queue_display()
            self.update_total_time()
            self.status.set("Queue cleared")

    def start_queue(self):
        """Start processing the order queue."""
        if self.running:
            return
        
        if not self.order_queue:
            messagebox.showinfo("No Orders", "Add drinks to queue first!")
            return

        self.running = True
        self.start_btn.config(state="disabled", bg="gray")
        self.clear_btn.config(state="disabled")
        self.status.set("Starting queue...")
        self.current_order_index = 0

        threading.Thread(target=self.process_queue, daemon=True).start()

    def process_queue(self):
        """Process all orders in FIFO order."""
        try:
            total_orders = len(self.order_queue)
            
            for order_idx, (juice_key, quantity) in enumerate(self.order_queue):
                self.current_order_index = order_idx
                drink_name = next((lbl for k, lbl in DRINKS if k == juice_key), juice_key)
                
                self.after(0, self.refresh_queue_display)
                
                # Process each drink in this order
                for drink_num in range(1, quantity + 1):
                    self.current_drink_in_order = drink_num
                    
                    # Update UI
                    self.after(0, lambda: self.current_label.config(
                        text=f"Order #{order_idx + 1}: {drink_name} ({drink_num}/{quantity})"))
                    self.after(0, lambda: self.status.set(
                        f"Making {drink_name} {drink_num}/{quantity}"))
                    
                    # Calculate progress
                    total_drinks = sum(qty for _, qty in self.order_queue)
                    completed_drinks = sum(qty for _, qty in self.order_queue[:order_idx])
                    completed_drinks += drink_num
                    progress = (completed_drinks / total_drinks) * 100
                    
                    self.after(0, lambda p=progress: self.progress_var.set(p))
                    self.after(0, lambda p=progress: self.progress_text.config(text=f"{p:.0f}%"))
                    
                    # Calculate time remaining
                    remaining_drinks = total_drinks - completed_drinks
                    avg_time = DRINK_TIME_ESTIMATE.get(juice_key, 45)
                    remaining_seconds = remaining_drinks * avg_time
                    remaining_min = int(remaining_seconds // 60)
                    remaining_sec = int(remaining_seconds % 60)
                    
                    self.after(0, lambda m=remaining_min, s=remaining_sec: 
                              self.time_remaining_label.config(text=f"Time: {m}m {s}s"))
                    
                    # Execute the drink program
                    make_drink(juice_key)
            
            # All done
            self.after(0, lambda: self.status.set("✓ All orders complete!"))
            self.after(0, lambda: self.current_label.config(text="Current: None"))
            self.after(0, lambda: self.progress_var.set(0))
            self.after(0, lambda: self.progress_text.config(text="0%"))
            self.after(0, lambda: messagebox.showinfo("Complete", "All orders finished!"))
            
        except Exception as e:
            self.after(0, lambda: self.status.set(f"Error: {e}"))
            self.after(0, lambda: messagebox.showerror("Order Failed", str(e)))
        
        finally:
            self.running = False
            self.order_queue.clear()
            self.after(0, lambda: self.start_btn.config(state="normal", bg="#2ecc71"))
            self.after(0, lambda: self.clear_btn.config(state="normal"))
            self.after(0, self.refresh_queue_display)
            self.after(0, self.update_total_time)
class DeveloperScreen(tk.Frame):
    def __init__(self, master, on_back):
        super().__init__(master)
        self.on_back = on_back
        self.status = tk.StringVar(value="Idle")

        tk.Label(self, text="Developer / Maintenance", font=("Arial", 20, "bold")).pack(pady=20)

        tk.Button(self, text="Open Teaching GUI", width=30, height=2,
                  command=self.open_teaching).pack(pady=8)

        tk.Button(self, text="Test Mango", width=30, height=2,
                  command=lambda: self.test_drink("mango")).pack(pady=6)

        tk.Button(self, text="Test Orange", width=30, height=2,
                  command=lambda: self.test_drink("orange")).pack(pady=6)

        tk.Button(self, text="Back to Customer", width=30, height=2,
                  command=self.on_back).pack(pady=16)

        tk.Label(self, textvariable=self.status, fg="blue", wraplength=600).pack(pady=10)

    def open_teaching(self):
        win = tk.Toplevel(self)
        win.title("ZKBot Teaching GUI")
        gui.MainWindow(win)

    def test_drink(self, key):
        def worker():
            try:
                self.set_status(f"Running test: {key}")
                make_drink(key)
                self.set_status("Test done.")
            except Exception as e:
                self.set_status(f"Error: {e}")
                messagebox.showerror("Error", str(e))

        threading.Thread(target=worker, daemon=True).start()

    def set_status(self, text):
        self.after(0, lambda: self.status.set(text))


if __name__ == "__main__":
    App().mainloop()
