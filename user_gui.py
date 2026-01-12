# user_gui.py

import tkinter as tk
from order_runner import run_order


class UserWindow(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.pack()
        self.create_widgets()

    def create_widgets(self):
        tk.Label(self, text="Select juice").pack(pady=10)

        tk.Button(
            self,
            text="Mango",
            command=lambda: run_order("mango"),
        ).pack(fill="x", padx=10, pady=2)

        tk.Button(
            self,
            text="Orange",
            command=lambda: run_order("orange"),
        ).pack(fill="x", padx=10, pady=2)

        tk.Button(
            self,
            text="Grape",
            command=lambda: run_order("grape"),
        ).pack(fill="x", padx=10, pady=2)

        tk.Button(
            self,
            text="Apple",
            command=lambda: run_order("apple"),
        ).pack(fill="x", padx=10, pady=2)


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Juice Dispenser")
    app = UserWindow(master=root)
    root.mainloop()
