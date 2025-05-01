"""
Supply chain functions for inventory simulations.
"""
import math
import numpy as np
from typing import Optional, Union, List, Dict, Any, Tuple

def generate_lead_time(
    supply_lt_mean: float,
    supply_lt_distribution: str,
    supply_lt_dispersion_parameter: Optional[float],
    min_lead_time: int = 1,
    round_to_int: bool = True
) -> Union[int, float]:
    """
    Generate lead time based on parameters.
    
    Args:
        supply_lt_mean: Mean lead time
        supply_lt_distribution: Distribution type ('normal', 'poisson', 'gamma', 'lognormal')
        supply_lt_dispersion_parameter: Dispersion parameter (std dev for normal, shape for gamma, etc.)
        min_lead_time: Minimum lead time
        round_to_int: Whether to round lead time to integer
        
    Returns:
        Generated lead time
    """
    # Validate inputs
    if supply_lt_mean <= 0:
        raise ValueError("supply_lt_mean must be positive")
    
    if supply_lt_distribution not in ['normal', 'poisson', 'gamma', 'lognormal']:
        raise ValueError(f"Invalid supply_lt_distribution: {supply_lt_distribution}")
    
    if supply_lt_dispersion_parameter is not None and supply_lt_dispersion_parameter < 0:
        raise ValueError("supply_lt_dispersion_parameter must be non-negative")
    
    # Generate lead time based on distribution
    if supply_lt_distribution == 'normal':
        if supply_lt_dispersion_parameter is None:
            raise ValueError("supply_lt_dispersion_parameter is required for normal distribution")
        
        # If dispersion parameter is 0, return the mean directly (deterministic case)
        if supply_lt_dispersion_parameter == 0:
            lead_time = supply_lt_mean
        else:
            # Generate lead time from normal distribution
            lead_time = np.random.normal(supply_lt_mean, supply_lt_dispersion_parameter)
    
    elif supply_lt_distribution == 'poisson':
        # Generate lead time from Poisson distribution
        lead_time = np.random.poisson(supply_lt_mean)
    
    elif supply_lt_distribution == 'gamma':
        if supply_lt_dispersion_parameter is None:
            raise ValueError("supply_lt_dispersion_parameter is required for gamma distribution")
        
        # For gamma, we use dispersion_parameter as the shape parameter
        # and calculate scale to maintain the desired mean
        shape = supply_lt_dispersion_parameter
        
        # If shape is 0, return the mean directly (deterministic case)
        if shape == 0:
            lead_time = supply_lt_mean
        else:
            scale = supply_lt_mean / shape
            # Generate lead time from gamma distribution
            lead_time = np.random.gamma(shape, scale)
    
    elif supply_lt_distribution == 'lognormal':
        if supply_lt_dispersion_parameter is None:
            raise ValueError("supply_lt_dispersion_parameter is required for lognormal distribution")
        
        # For lognormal, we need to convert mean and std to mu and sigma
        # If X is lognormal, then log(X) is normal with parameters mu and sigma
        # E[X] = exp(mu + sigma^2/2)
        # Var[X] = (exp(sigma^2) - 1) * exp(2*mu + sigma^2)
        
        # We use dispersion_parameter as the coefficient of variation (CV = std/mean)
        cv = supply_lt_dispersion_parameter
        
        # If dispersion parameter is 0, return the mean directly (deterministic case)
        if cv == 0:
            lead_time = supply_lt_mean
        else:
            # Calculate sigma from CV
            sigma = np.sqrt(np.log(1 + cv**2))
            
            # Calculate mu from mean and sigma
            mu = np.log(supply_lt_mean) - (sigma**2) / 2
            
            # Generate lead time from lognormal distribution
            lead_time = np.random.lognormal(mu, sigma)
    
    # Round to integer if requested
    if round_to_int:
        lead_time = round(lead_time)
    
    # Apply minimum lead time
    lead_time = max(min_lead_time, lead_time)
    
    return lead_time

def calculate_supply_due_date(
    current_day: int,
    lead_time: Optional[int] = None,
    supply_lt_mean: Optional[float] = None,
    supply_lt_distribution: Optional[str] = None,
    supply_lt_dispersion_parameter: Optional[float] = None,
    min_lead_time: int = 1
) -> int:
    """
    Calculate the due date for a supply order.
    
    Args:
        current_day: Current simulation day
        lead_time: Lead time (if None, will be generated)
        supply_lt_mean: Mean lead time (used if lead_time is None)
        supply_lt_distribution: Distribution type (used if lead_time is None)
        supply_lt_dispersion_parameter: Dispersion parameter (used if lead_time is None)
        min_lead_time: Minimum lead time
        
    Returns:
        Due date for the supply order
    """
    # If lead time is provided, use it
    if lead_time is not None:
        if lead_time < 0:
            raise ValueError("lead_time must be non-negative")
        
        return current_day + lead_time
    
    # Otherwise, generate lead time
    if supply_lt_mean is None or supply_lt_distribution is None:
        raise ValueError("supply_lt_mean and supply_lt_distribution are required if lead_time is None")
    
    lead_time = generate_lead_time(
        supply_lt_mean=supply_lt_mean,
        supply_lt_distribution=supply_lt_distribution,
        supply_lt_dispersion_parameter=supply_lt_dispersion_parameter,
        min_lead_time=min_lead_time,
        round_to_int=True
    )
    
    return current_day + lead_time

def generate_supply_orders(
    current_day: int,
    inventory_reference: float,
    reorder_point: float,
    order_quantity_method: str,
    supply_lt_mean: float,
    supply_lt_distribution: str,
    supply_lt_dispersion_parameter: Optional[float] = None,
    reorder_quantity: Optional[float] = None,
    max_quantity: Optional[float] = None,
    max_days: Optional[float] = None,
    forecast: Optional[Union[float, List[float]]] = None,
    min_lead_time: int = 1,
    moving_average_window: int = 30,
    reorder_method: str = "onhand_static"
) -> List[Dict[str, Any]]:
    """
    Generate supply orders based on inventory reference and reorder policy.
    
    Args:
        current_day: Current simulation day
        inventory_reference: Inventory reference level
        reorder_point: Reorder point
        order_quantity_method: Method for calculating order quantity
        supply_lt_mean: Mean lead time
        supply_lt_distribution: Distribution type
        supply_lt_dispersion_parameter: Dispersion parameter
        reorder_quantity: Fixed reorder quantity (for 'fixed' method)
        max_quantity: Maximum inventory level (for 'max_quantity' method)
        max_days: Maximum days of inventory (for 'max_days' method)
        forecast: Forecast demand (for 'max_days' method)
        min_lead_time: Minimum lead time
        moving_average_window: Window size for moving average calculation
        reorder_method: Reorder method (onhand_static, onhand_dynamic, projected_static, projected_dynamic)
        
    Returns:
        List of supply orders
    """
    # Check if reorder is needed
    if inventory_reference > reorder_point:
        return []
    
    # Import here to avoid circular imports
    from pyps_invsim.core.inventory import calculate_effective_reorder_quantity
    
    # Calculate order quantity using the function from inventory.py
    order_quantity = calculate_effective_reorder_quantity(
        order_quantity_method=order_quantity_method,
        reorder_quantity=reorder_quantity,
        max_quantity=max_quantity,
        max_days=max_days,
        inventory_reference=inventory_reference,
        forecast=forecast,
        moving_average_window=moving_average_window,
        reorder_method=reorder_method
    )
    
    # Round up to the nearest integer (should already be rounded by _calculate_order_quantity)
    order_quantity = math.ceil(order_quantity)
    
    # If order quantity is zero, no orders are generated
    if order_quantity <= 0:
        return []
    
    # Generate lead time
    lead_time = generate_lead_time(
        supply_lt_mean=supply_lt_mean,
        supply_lt_distribution=supply_lt_distribution,
        supply_lt_dispersion_parameter=supply_lt_dispersion_parameter,
        min_lead_time=min_lead_time,
        round_to_int=True
    )
    
    # Calculate due date
    due_date = current_day + lead_time
    
    # Create order
    order = {
        'day': current_day,
        'quantity': order_quantity,
        'arrival': due_date,
        'lead_time': lead_time,
        'due_date': due_date
    }
    
    return [order]