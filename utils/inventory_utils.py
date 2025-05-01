"""
Utility functions for inventory calculations.
"""
from typing import List, Dict, Any, Optional, Union, Tuple
import numpy as np
from pyps_invsim.core.forecasting import calculate_moving_average

def calculate_stockout_days(
    inventory_levels: List[float]
) -> int:
    """
    Calculate the number of stockout days (days with inventory <= 0).
    
    Args:
        inventory_levels: List of inventory levels
        
    Returns:
        Number of stockout days
    """
    if not inventory_levels:
        return 0
    
    # Count days with inventory <= 0
    stockout_days = sum(1 for inv in inventory_levels if inv <= 0)
    
    return stockout_days

def calculate_stockout_days_for_scenarios(
    all_scenarios: List[List[float]]
) -> List[int]:
    """
    Calculate stockout days for multiple scenarios.
    
    Args:
        all_scenarios: List of inventory level lists for each scenario
        
    Returns:
        List of stockout days for each scenario
    """
    stockout_days_per_scenario = []
    
    for scenario in all_scenarios:
        stockout_days = calculate_stockout_days(scenario)
        stockout_days_per_scenario.append(stockout_days)
    
    return stockout_days_per_scenario

def calculate_stockout_statistics(
    stockout_days_per_scenario: List[int],
    round_decimals: int = 2
) -> Dict[str, float]:
    """
    Calculate statistics for stockout days.
    
    Args:
        stockout_days_per_scenario: List of stockout days values
        round_decimals: Number of decimal places to round to
        
    Returns:
        Dictionary of statistics
    """
    if not stockout_days_per_scenario:
        return {
            'median': 0.0,
            'percentile_95': 0.0,
            'q75': 0.0,
            'q25': 0.0,
            'iqr': 0.0
        }
    
    median = round(np.median(stockout_days_per_scenario), round_decimals)
    percentile_95 = round(np.percentile(stockout_days_per_scenario, 95), round_decimals)
    q75 = round(np.percentile(stockout_days_per_scenario, 75), round_decimals)
    q25 = round(np.percentile(stockout_days_per_scenario, 25), round_decimals)
    iqr = round(q75 - q25, round_decimals)
    
    return {
        'median': median,
        'percentile_95': percentile_95,
        'q75': q75,
        'q25': q25,
        'iqr': iqr
    }

def calculate_inventory_days(
    inventory_levels: List[float],
    demand_history: List[float],
    moving_average_window: int
) -> float:
    """
    Calculate inventory days (inventory / daily demand) for a single scenario.
    
    Args:
        inventory_levels: List of inventory levels
        demand_history: List of demand values
        moving_average_window: Window size for moving average calculation
        
    Returns:
        Inventory days value
    """
    if not inventory_levels or not demand_history:
        return 0.0
    
    # Calculate average inventory
    avg_inventory = sum(inventory_levels) / len(inventory_levels)
    
    # Calculate average demand using moving average
    avg_demand = 0.0
    if demand_history:
        if len(demand_history) < moving_average_window:
            # For early periods, use all available data
            avg_demand = sum(demand_history) / len(demand_history)
        else:
            # Use moving average window
            avg_demand = sum(demand_history[-moving_average_window:]) / moving_average_window
    
    # Calculate inventory days (inventory / daily demand)
    if avg_demand > 0:
        inventory_days = avg_inventory / avg_demand
    else:
        inventory_days = 0.0
    
    return inventory_days

def calculate_inventory_days_for_scenarios(
    all_scenarios: List[List[float]],
    all_demands: List[List[float]],
    moving_average_window: int
) -> List[float]:
    """
    Calculate inventory days for multiple scenarios.
    
    Args:
        all_scenarios: List of inventory level lists for each scenario
        all_demands: List of demand lists for each scenario
        moving_average_window: Window size for moving average calculation
        
    Returns:
        List of inventory days values for each scenario
    """
    inventory_days_per_scenario = []
    
    if all_scenarios and all_demands:
        # Make sure we have the same number of scenarios for both inventory and demand
        num_scenarios = min(len(all_scenarios), len(all_demands))
        
        for i in range(num_scenarios):
            scenario = all_scenarios[i]
            demands = all_demands[i]
            
            inventory_days = calculate_inventory_days(
                inventory_levels=scenario,
                demand_history=demands,
                moving_average_window=moving_average_window
            )
            
            inventory_days_per_scenario.append(inventory_days)
    
    return inventory_days_per_scenario

def calculate_inventory_statistics(
    inventory_days_per_scenario: List[float],
    round_decimals: int = 2
) -> Dict[str, float]:
    """
    Calculate statistics for inventory days.
    
    Args:
        inventory_days_per_scenario: List of inventory days values
        round_decimals: Number of decimal places to round to
        
    Returns:
        Dictionary of statistics
    """
    if not inventory_days_per_scenario:
        return {
            'median': 0.0,
            'percentile_95': 0.0,
            'q75': 0.0,
            'q25': 0.0,
            'iqr': 0.0
        }
    
    median = round(np.median(inventory_days_per_scenario), round_decimals)
    percentile_95 = round(np.percentile(inventory_days_per_scenario, 95), round_decimals)
    q75 = round(np.percentile(inventory_days_per_scenario, 75), round_decimals)
    q25 = round(np.percentile(inventory_days_per_scenario, 25), round_decimals)
    iqr = round(q75 - q25, round_decimals)
    
    return {
        'median': median,
        'percentile_95': percentile_95,
        'q75': q75,
        'q25': q25,
        'iqr': iqr
    }