"""
Command-line interface utility functions for inventory simulations.
"""
import argparse
from typing import Dict, List, Any, Optional
import os
from pathlib import Path

from pyps_invsim.utils.path_utils import get_logs_dir, get_excel_dir

def create_simulation_argument_parser():
    """
    Create an argument parser for inventory simulation.
    
    Returns:
        ArgumentParser object
    """
    parser = argparse.ArgumentParser(description='Run inventory simulation')
    
    # File paths
    parser.add_argument('--excel_file', type=str, help='Path to Excel file with parameters')
    parser.add_argument('--table_name', type=str, default='InvSim_Parameters', help='Name of table in Excel file')
    parser.add_argument('--log_dir', type=str, default=str(get_logs_dir()), help='Directory for log files')
    
    # Simulation parameters
    parser.add_argument('--num_scenarios', type=int, help='Number of scenarios to run')
    parser.add_argument('--num_periods', type=int, help='Number of periods to simulate')
    parser.add_argument('--start_inventory', type=float, help='Starting inventory level')
    
    # Demand parameters
    parser.add_argument('--demand_mean', type=float, help='Mean demand')
    parser.add_argument('--demand_distribution', type=str, choices=['normal', 'poisson', 'gamma', 'lognormal'], help='Demand distribution')
    parser.add_argument('--demand_dispersion_parameter', type=float, help='Dispersion parameter for demand distribution')
    parser.add_argument('--demand_pattern', type=str, choices=['flat', 'seasonal'], help='Demand pattern')
    parser.add_argument('--seasonality_weight', type=float, help='Weight of seasonality effect')
    parser.add_argument('--trend_weight', type=float, help='Weight of trend effect')
    parser.add_argument('--trend_monthly_rate', type=float, help='Monthly growth rate for trend')
    
    # Supply parameters
    parser.add_argument('--supply_lt_mean', type=float, help='Mean lead time for supply')
    parser.add_argument('--supply_lt_distribution', type=str, choices=['normal', 'poisson', 'gamma', 'lognormal'], help='Lead time distribution')
    parser.add_argument('--supply_lt_dispersion_parameter', type=float, help='Dispersion parameter for lead time distribution')
    
    # Reorder policy parameters
    parser.add_argument('--reorder_point', type=float, help='Reorder point')
    parser.add_argument('--reorder_quantity', type=float, help='Reorder quantity')
    parser.add_argument('--reorder_method', type=str, choices=['onhand_static', 'onhand_dynamic', 'projected_static', 'projected_dynamic'], help='Reorder method')
    parser.add_argument('--order_quantity_method', type=str, choices=['fixed', 'max_quantity', 'max_days'], help='Order quantity method')
    parser.add_argument('--max_quantity', type=float, help='Maximum inventory level')
    parser.add_argument('--min_days', type=float, help='Minimum days of inventory')
    parser.add_argument('--max_days', type=float, help='Maximum days of inventory')
    
    # Forecast parameters
    parser.add_argument('--forecast_type', type=str, choices=['naive', 'moving_average'], help='Forecast type')
    parser.add_argument('--moving_average_window', type=int, help='Window size for moving average forecast')
    parser.add_argument('--early_period_strategy', type=str, choices=['use_available', 'use_mean', 'use_default'], help='Strategy for early period forecasting')
    
    # Logging parameters
    parser.add_argument('--logging_level', type=str, choices=['off', 'last_run', 'archive'], default='last_run', help='Logging level')
    parser.add_argument('--log_format', type=str, choices=['csv', 'json', 'pickle'], default='csv', help='Log file format')
    parser.add_argument('--scenario_sampling', type=int, help='Log every nth scenario')
    parser.add_argument('--period_sampling', type=int, help='Log every nth period')
    parser.add_argument('--detailed_logging', action='store_true', help='Enable detailed logging')
    
    # Analysis parameters
    parser.add_argument('--detect_anomalies', action='store_true', help='Detect anomalies in simulation data')
    parser.add_argument('--anomaly_threshold', type=float, default=2.0, help='Threshold multiplier for anomaly detection')
    parser.add_argument('--create_plots', action='store_true', help='Create visualization plots')
    
    return parser

def parse_simulation_arguments():
    """
    Parse command-line arguments for inventory simulation.
    
    Returns:
        Parsed arguments
    """
    parser = create_simulation_argument_parser()
    return parser.parse_args()

def args_to_dict(args):
    """
    Convert parsed arguments to a dictionary.
    
    Args:
        args: Parsed arguments
        
    Returns:
        Dictionary of arguments
    """
    return {k: v for k, v in vars(args).items() if v is not None}

def validate_cli_arguments(args):
    """
    Validate command-line arguments.
    
    Args:
        args: Parsed arguments
        
    Raises:
        ValueError: If arguments are invalid
    """
    # Check that Excel file exists if specified
    if args.excel_file and not os.path.exists(args.excel_file):
        raise ValueError(f"Excel file not found: {args.excel_file}")
    
    # Check that log directory is writable
    log_dir = Path(args.log_dir)
    if not log_dir.exists():
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ValueError(f"Cannot create log directory: {e}")
    
    # Check numeric parameters
    if args.num_scenarios is not None and args.num_scenarios <= 0:
        raise ValueError("num_scenarios must be positive")
    
    if args.num_periods is not None and args.num_periods <= 0:
        raise ValueError("num_periods must be positive")
    
    if args.start_inventory is not None and args.start_inventory < 0:
        raise ValueError("start_inventory must be non-negative")
    
    if args.demand_mean is not None and args.demand_mean < 0:
        raise ValueError("demand_mean must be non-negative")
    
    if args.supply_lt_mean is not None and args.supply_lt_mean <= 0:
        raise ValueError("supply_lt_mean must be positive")
    
    if args.moving_average_window is not None and args.moving_average_window <= 0:
        raise ValueError("moving_average_window must be positive")