# app.py
#
# Customer kiosk: owner login → customer ordering → developer settings.

import tkinter as tk
from tkinter import messagebox
import threading

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


class CustomerScreen(tk.Frame):
    def __init__(self, master, on_open_dev):
        super().__init__(master)
        self.on_open_dev = on_open_dev
        self.order = []
        self.running = False

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

        right = tk.Frame(body, bd=1, relief="solid")
        right.pack(side="right", fill="y", padx=(10, 0))

        # Drinks buttons
        tk.Label(left, text="Select Drinks", font=("Arial", 14, "bold")).pack(pady=5)

        grid = tk.Frame(left)
        grid.pack(pady=10)

        for i, (key, label) in enumerate(DRINKS):
            btn = tk.Button(grid, text=f"Add {label}", width=22, height=2,
                            command=lambda k=key: self.add(k))
            btn.grid(row=i // 2, column=i % 2, padx=8, pady=8)

        # Cart
        tk.Label(right, text="Order List", font=("Arial", 14, "bold")).pack(pady=10)
        self.listbox = tk.Listbox(right, width=28, height=14)
        self.listbox.pack(padx=10, pady=5)

        btn_row = tk.Frame(right)
        btn_row.pack(pady=8)

        tk.Button(btn_row, text="Clear", width=10, command=self.clear).pack(side="left", padx=5)
        self.start_btn = tk.Button(btn_row, text="Start", width=10, command=self.start)
        self.start_btn.pack(side="left", padx=5)

        self.status = tk.StringVar(value="Idle")
        tk.Label(right, textvariable=self.status, fg="green", wraplength=220).pack(pady=8)

    def add(self, juice_key):
        if self.running:
            return
        self.order.append(juice_key)
        self.refresh()

    def clear(self):
        if self.running:
            return
        self.order.clear()
        self.refresh()

    def refresh(self):
        self.listbox.delete(0, tk.END)
        for idx, key in enumerate(self.order, start=1):
            name = next((lbl for k, lbl in DRINKS if k == key), key)
            self.listbox.insert(tk.END, f"{idx}. {name}")

    def start(self):
        if self.running:
            return
        if not self.order:
            messagebox.showinfo("No order", "Add at least one drink.")
            return

        self.running = True
        self.start_btn.config(state="disabled")
        self.set_status("Starting...")

        threading.Thread(target=self.run_order, daemon=True).start()

    def run_order(self):
        try:
            for i, key in enumerate(self.order, start=1):
                self.set_status(f"Making {i}/{len(self.order)} : {key}")
                make_drink(key)
            self.set_status("Done.")
        except Exception as e:
            self.set_status(f"Error: {e}")
            messagebox.showerror("Order failed", str(e))
        finally:
            self.running = False
            self.start_btn.config(state="normal")

    def set_status(self, text):
        self.after(0, lambda: self.status.set(text))


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
