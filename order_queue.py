# order_queue.py
# Order Queue Management for Juice Kiosk

from dataclasses import dataclass
from typing import List, Optional
from models import Program
import time


@dataclass
class Order:
    """Represents a customer order."""
    order_id: int
    flavor: str
    quantity: int
    program: Program
    status: str = "Pending"  # Pending, Processing, Completed
    
    def __str__(self):
        return f"#{self.order_id} {self.flavor} x{self.quantity}"


class OrderQueue:
    """Manages FIFO order queue."""
    
    def __init__(self):
        self.orders: List[Order] = []
        self.next_id = 1
        self.is_processing = False
        
    def add_order(self, flavor: str, quantity: int, program: Program) -> Order:
        """Add new order to queue."""
        order = Order(
            order_id=self.next_id,
            flavor=flavor,
            quantity=quantity,
            program=program
        )
        self.orders.append(order)
        self.next_id += 1
        return order
    
    def get_current_order(self) -> Optional[Order]:
        """Get the order currently being processed."""
        for order in self.orders:
            if order.status == "Processing":
                return order
        return None
    
    def get_next_pending(self) -> Optional[Order]:
        """Get next pending order (FIFO)."""
        for order in self.orders:
            if order.status == "Pending":
                return order
        return None
    
    def remove_completed(self):
        """Remove completed orders from queue."""
        self.orders = [o for o in self.orders if o.status != "Completed"]
    
    def clear_all(self):
        """Clear all orders."""
        self.orders.clear()
    
    def get_pending_count(self) -> int:
        """Count pending orders."""
        return sum(1 for o in self.orders if o.status == "Pending")
    
    def get_total_count(self) -> int:
        """Total orders in queue."""
        return len(self.orders)


def estimate_program_time(program: Program) -> float:
    """
    Estimate program execution time in seconds.
    Based on delays + estimated move times.
    """
    if not program.steps:
        return 0.0
    
    total_time = 0.0
    
    for step in program.steps:
        # Add delay time
        total_time += step.delay
        
        # Estimate move time based on feedrate
        # Assume average move distance of 100mm
        # Time = Distance / Speed (converted to seconds)
        if step.f and step.f > 0:
            # F is in mm/min, convert to seconds
            # Assuming 100mm average move
            move_time = (100 / step.f) * 60  # seconds
            total_time += move_time
        else:
            # Default 2 seconds if no feedrate
            total_time += 2.0
    
    return total_time


def format_time(seconds: float) -> str:
    """Format seconds to 'Xm Ys' format."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m {secs}s"
