"""
Parameter loading and validation functions for inventory simulations.
"""
from typing import Dict, List, Any, Optional
import os
from pathlib import Path

from pyps_invsim.utils.excel_utils import load_excel_parameters
from pyps_invsim.utils.config_utils import load_default_parameters, merge_parameters
from pyps_invsim.utils.path_utils import find_project_root, get_excel_dir, get_config_dir, get_invsim_excel_file

def load_simulation_parameters(
    excel_filepath: Optional[str] = None,
    table_name: str = "InvSim_Parameters",
    required_vars: Optional[List[str]] = None,
    use_defaults: bool = True,
    config_filepath: Optional[str] = None
) -> Dict[str, Any]:
    """
    Load simulation parameters from Excel file and optionally merge with defaults.
    
    Args:
        excel_filepath: Path to the Excel file (if None, uses default location)
        table_name: Name of the table in Excel
        required_vars: List of required variables
        use_defaults: Whether to load and merge default parameters
        config_filepath: Path to the config file (if None, uses default location)
        
    Returns:
        Dictionary of simulation parameters
    """
    # If no excel_filepath provided, use the function to find the Excel file
    if excel_filepath is None:
        excel_filepath = str(get_invsim_excel_file())
    
    # Load parameters from Excel
    excel_params = load_excel_parameters(
        filepath=excel_filepath,
        table_name=table_name
    )
    
    # If not using defaults, return Excel parameters directly
    if not use_defaults:
        return excel_params
    
    # Load default parameters
    if config_filepath is None:
        config_dir = get_config_dir()
        config_filepath = str(config_dir / 'default_parameters.yaml')
    
    default_params = load_default_parameters(config_filepath)
    
    # Merge parameters (Excel parameters take precedence)
    merged_params = merge_parameters(default_params, excel_params)
    
    return merged_params

def validate_parameters(params: Dict[str, Any], required_vars: List[str]) -> None:
    """
    Validate that all required parameters are present and have valid values.
    
    Args:
        params: Dictionary of parameters
        required_vars: List of required variable names
        
    Raises:
        ValueError: If any required parameter is missing or invalid
    """
    # Check for missing parameters
    missing_params = [var for var in required_vars if var not in params]
    if missing_params:
        raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")
    
    # Validate specific parameters
    if 'num_periods' in params and params['num_periods'] <= 0:
        raise ValueError("num_periods must be positive")
    
    if 'num_scenarios' in params and params['num_scenarios'] <= 0:
        raise ValueError("num_scenarios must be positive")
    
    if 'demand_mean' in params and params['demand_mean'] < 0:
        raise ValueError("demand_mean must be non-negative")
    
    if 'start_inventory' in params and params['start_inventory'] < 0:
        raise ValueError("start_inventory must be non-negative")
    
    if 'supply_lt_mean' in params and params['supply_lt_mean'] <= 0:
        raise ValueError("supply_lt_mean must be positive")
    
    # Validate reorder method
    if 'reorder_method' in params:
        valid_reorder_methods = ["onhand_static", "onhand_dynamic", "projected_static", "projected_dynamic"]
        if params['reorder_method'] not in valid_reorder_methods:
            raise ValueError(f"reorder_method must be one of: {', '.join(valid_reorder_methods)}")
    
    # Validate order quantity method
    if 'order_quantity_method' in params:
        valid_order_methods = ["fixed", "max_quantity", "max_days"]
        if params['order_quantity_method'] not in valid_order_methods:
            raise ValueError(f"order_quantity_method must be one of: {', '.join(valid_order_methods)}")
    
    # Validate demand distribution
    if 'demand_distribution' in params:
        valid_distributions = ["normal", "poisson", "gamma", "lognormal"]
        if params['demand_distribution'] not in valid_distributions:
            raise ValueError(f"demand_distribution must be one of: {', '.join(valid_distributions)}")
    
    # Validate seasonal_pattern if provided
    if 'seasonal_pattern' in params and params['seasonal_pattern'] is not None:
        if not isinstance(params['seasonal_pattern'], str):
            raise ValueError("seasonal_pattern must be a string (comma-separated values)")
        
        # Try to parse the comma-separated values
        try:
            values = [float(x.strip()) for x in params['seasonal_pattern'].split(',') if x.strip()]
            if not values:
                raise ValueError("seasonal_pattern must contain at least one value")
        except ValueError:
            raise ValueError("seasonal_pattern must contain valid numeric values")
    
    # Validate forecast type
    if 'forecast_type' in params:
        valid_forecast_types = ["naive", "moving_average"]
        if params['forecast_type'] not in valid_forecast_types:
            raise ValueError(f"forecast_type must be one of: {', '.join(valid_forecast_types)}")

def get_required_parameters() -> List[str]:
    """
    Get the list of required parameters for the inventory simulation.
    
    Returns:
        List of required parameter names
    """
    return [
        # Inventory parameters
        'start_inventory',
        
        # Demand parameters
        'demand_mean',
        'demand_distribution',
        'demand_dispersion_parameter',
        'seasonal_pattern',
        
        # Supply parameters
        'reorder_point',
        'reorder_quantity',
        'supply_lt_mean',
        'supply_lt_distribution',
        'supply_lt_dispersion_parameter',
        
        # Reorder policy parameters
        'reorder_method',
        'order_quantity_method',
        'max_quantity',
        'min_days',
        'max_days',
        
        # Forecast parameters
        'forecast_type',
        'moving_average_window',
        
        # Simulation parameters
        'num_periods',
        'num_scenarios'
    ]