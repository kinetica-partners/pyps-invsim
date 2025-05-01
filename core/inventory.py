"""
Inventory management functions for inventory simulations.
"""
import math
from typing import List, Dict, Any, Optional, Union, Tuple

def update_inventory(
    current_inventory: float,
    demand: float,
    received_supply: float = 0
) -> float:
    """
    Update inventory level based on demand and received supply.
    
    Args:
        current_inventory: Current inventory level
        demand: Demand to be fulfilled
        received_supply: Supply received
        
    Returns:
        Updated inventory level
    """
    # Add received supply
    updated_inventory = current_inventory + received_supply
    
    # Subtract demand (but don't go below zero)
    updated_inventory = max(0, updated_inventory - demand)
    
    return updated_inventory

def process_pending_orders(
    pending_orders: List[Dict[str, Any]],
    current_day: int
) -> float:
    """
    Process pending orders and return the total supply received.
    
    Args:
        pending_orders: List of pending orders
        current_day: Current simulation day
        
    Returns:
        Total supply received
    """
    if not pending_orders:
        return 0
    
    # Find orders that are due today
    due_orders = [order for order in pending_orders if order['arrival'] == current_day]
    
    # Calculate total supply received
    total_supply = sum(order['quantity'] for order in due_orders)
    
    # Remove processed orders from pending orders
    for order in due_orders:
        pending_orders.remove(order)
    
    return total_supply

def check_reorder_needed(
    inventory_reference: float,
    reorder_point: float
) -> bool:
    """
    Check if a reorder is needed based on inventory reference and reorder point.
    
    Args:
        inventory_reference: Inventory reference level
        reorder_point: Reorder point
        
    Returns:
        True if reorder is needed, False otherwise
    """
    return inventory_reference <= reorder_point

def calculate_inventory_reference(
    current_inventory: float,
    pending_orders: List[Dict[str, Any]],
    forecast: Optional[Union[float, List[float]]],
    current_day: int,
    reorder_method: str,
    supply_lt_mean: float
) -> float:
    """
    Calculate inventory reference for reorder decisions.
    
    Args:
        current_inventory: Current inventory level
        pending_orders: List of pending orders
        forecast: Forecast demand (single value or list)
        current_day: Current simulation day
        reorder_method: Method for calculating inventory reference
        supply_lt_mean: Mean lead time for supply
        
    Returns:
        Inventory reference level
    """
    # Start with current inventory
    inventory_reference = current_inventory
    
    # Add ALL pending orders regardless of policy type
    # This ensures we don't place duplicate orders when orders are already in the pipeline
    pending_supply = sum(order['quantity'] for order in pending_orders)
    inventory_reference += pending_supply
    
    # For projected methods, also subtract forecast demand
    if reorder_method.startswith("projected"):
        # Convert forecast to a list if it's a single value
        if forecast is None:
            forecast_list = []
        elif isinstance(forecast, (int, float)):
            forecast_list = [forecast] * int(supply_lt_mean)
        else:
            forecast_list = forecast
        
        # Subtract forecast demand for each day in the forecast horizon
        for day_offset in range(1, int(supply_lt_mean) + 1):
            # Subtract forecast demand for this day
            if day_offset <= len(forecast_list):
                day_demand = forecast_list[day_offset - 1]
                inventory_reference = max(0, inventory_reference - day_demand)
    
    return inventory_reference

def calculate_effective_reorder_point(
    reorder_method: str,
    reorder_point: float,
    min_days: Optional[float],
    forecast: Optional[Union[float, List[float]]]
) -> float:
    """
    Calculate effective reorder point based on method.
    
    Args:
        reorder_method: Method for calculating reorder point
        reorder_point: Static reorder point
        min_days: Minimum days of inventory (for dynamic methods)
        forecast: Forecast demand (single value or list)
        
    Returns:
        Effective reorder point
    """
    # For static methods, just return the static reorder point
    if reorder_method.endswith("static"):
        return reorder_point
    
    # For dynamic methods, calculate based on forecast and min_days
    elif reorder_method.endswith("dynamic"):
        if min_days is None:
            raise ValueError("min_days is required for dynamic reorder methods")
        
        # Convert forecast to a single value if it's a list
        if forecast is None:
            avg_forecast = 0
        elif isinstance(forecast, list):
            avg_forecast = sum(forecast) / len(forecast) if forecast else 0
        else:
            avg_forecast = forecast
        
        # Calculate dynamic reorder point
        return avg_forecast * min_days
    
    else:
        raise ValueError(f"Invalid reorder method: {reorder_method}")

def _calculate_max_days_order_quantity(
    max_days: float,
    max_quantity: Optional[float],
    inventory_reference: float,
    forecast: Optional[Union[float, List[float]]],
    moving_average_window: int = 30
) -> float:
    """
    Helper function to calculate order quantity using the max_days method.
    
    Args:
        max_days: Maximum days of inventory
        max_quantity: Maximum inventory level
        inventory_reference: Inventory reference level
        forecast: Forecast demand (single value or list)
        moving_average_window: Window size for moving average calculation
        
    Returns:
        Order quantity
    """
    # Check if we have enough forecast data (early periods check)
    if forecast is None or (isinstance(forecast, list) and len(forecast) < moving_average_window):
        # For early periods (days < moving_average_window), use max_quantity - inventory_reference
        if max_quantity is not None:
            # Use max_quantity - inventory_reference for early periods
            # But cap it at a reasonable value based on the forecast
            if forecast is not None:
                avg_forecast = sum(forecast) / len(forecast) if isinstance(forecast, list) else forecast
                # Cap at max_days * avg_forecast
                max_order = avg_forecast * max_days
                return max(0, min(max_quantity - inventory_reference, max_order))
            else:
                return max(0, max_quantity - inventory_reference)
        else:
            return 0
    else:
        # Convert forecast to a single value if it's a list
        if forecast is None:
            avg_forecast = 0
        elif isinstance(forecast, list):
            avg_forecast = sum(forecast) / len(forecast) if forecast else 0
        else:
            avg_forecast = forecast
        
        # Calculate target inventory level
        target_level = avg_forecast * max_days
        
        # Calculate order quantity
        result = max(0, target_level - inventory_reference)
        
        # Cap the order quantity at max_quantity if provided
        if max_quantity is not None:
            result = min(result, max_quantity)
        
        return result

def calculate_effective_reorder_quantity(
    order_quantity_method: str,
    reorder_quantity: Optional[float],
    max_quantity: Optional[float],
    max_days: Optional[float],
    inventory_reference: float,
    forecast: Optional[Union[float, List[float]]],
    moving_average_window: int = 30,
    reorder_method: str = "onhand_static"
) -> float:
    """
    Calculate effective reorder quantity based on method.
    
    Args:
        order_quantity_method: Method for calculating order quantity
        reorder_quantity: Static reorder quantity
        max_quantity: Maximum inventory level (for max_quantity method)
        max_days: Maximum days of inventory (for max_days method)
        inventory_reference: Inventory reference level
        forecast: Forecast demand (single value or list)
        moving_average_window: Window size for moving average calculation
        reorder_method: Reorder method (onhand_static, onhand_dynamic, projected_static, projected_dynamic)
        
    Returns:
        Effective reorder quantity (rounded up to the nearest integer)
    """
    # Calculate the order quantity based on the reorder method
    result = 0.0
    
    # For dynamic policies (onhand_dynamic and projected_dynamic), always use max_days calculation
    if reorder_method.endswith("_dynamic"):
        if max_days is None:
            raise ValueError("max_days is required for dynamic reorder methods")
        
        result = _calculate_max_days_order_quantity(
            max_days=max_days,
            max_quantity=max_quantity,
            inventory_reference=inventory_reference,
            forecast=forecast,
            moving_average_window=moving_average_window
        )
    
    # For static policies (onhand_static and projected_static), respect the order_quantity_method
    elif reorder_method.endswith("_static"):
        # Handle fixed order quantity method
        if order_quantity_method == "fixed":
            if reorder_quantity is None:
                raise ValueError("reorder_quantity is required for fixed order quantity method")
            result = reorder_quantity
        
        # Handle max_quantity method
        elif order_quantity_method == "max_quantity":
            if max_quantity is None:
                raise ValueError("max_quantity is required for max_quantity order method")
            result = max(0, max_quantity - inventory_reference)
        
        # Handle max_days method
        elif order_quantity_method == "max_days":
            if max_days is None:
                raise ValueError("max_days is required for max_days order method")
            
            result = _calculate_max_days_order_quantity(
                max_days=max_days,
                max_quantity=max_quantity,
                inventory_reference=inventory_reference,
                forecast=forecast,
                moving_average_window=moving_average_window
            )
        else:
            raise ValueError(f"Invalid order quantity method: {order_quantity_method}")
    
    # For backward compatibility or unknown reorder methods
    else:
        # Handle fixed order quantity method
        if order_quantity_method == "fixed":
            if reorder_quantity is None:
                raise ValueError("reorder_quantity is required for fixed order quantity method")
            result = reorder_quantity
        
        # Handle max_quantity method
        elif order_quantity_method == "max_quantity":
            if max_quantity is None:
                raise ValueError("max_quantity is required for max_quantity order method")
            result = max(0, max_quantity - inventory_reference)
        
        # Handle max_days method
        elif order_quantity_method == "max_days":
            if max_days is None:
                raise ValueError("max_days is required for max_days order method")
            
            result = _calculate_max_days_order_quantity(
                max_days=max_days,
                max_quantity=max_quantity,
                inventory_reference=inventory_reference,
                forecast=forecast,
                moving_average_window=moving_average_window
            )
        else:
            raise ValueError(f"Invalid order quantity method: {order_quantity_method}")
    
    # Round up to the nearest integer
    return math.ceil(result)