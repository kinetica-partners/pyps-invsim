"""
Level 1 inventory simulation module.
"""
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple
import pandas as pd
import os
from pathlib import Path
import datetime
import xlwings as xw

# Setup imports to work both as package and standalone project
from pyps_invsim.utils.import_helper import setup_imports
setup_imports()

# Now imports will work both when running as a package and as a standalone project
from pyps_invsim.core.demand import generate_demand
from pyps_invsim.core.supply import generate_lead_time, calculate_supply_due_date, generate_supply_orders
from pyps_invsim.core.inventory import (
    update_inventory, process_pending_orders, check_reorder_needed,
    calculate_inventory_reference, calculate_effective_reorder_point,
    calculate_effective_reorder_quantity
)
from pyps_invsim.core.forecasting import generate_forecast, calculate_rolling_forecast
from pyps_invsim.utils.excel_utils import load_excel_parameters, write_simulation_csv
from pyps_invsim.logging.simulation_logger import SimulationLogger, LoggingLevel, NullLogger
from pyps_invsim.utils.path_utils import get_invsim_excel_file

def detect_anomalies(results, threshold=2.0):
    """
    Detect anomalies in simulation results.
    
    Args:
        results: List of simulation results
        threshold: Threshold multiplier for anomaly detection
        
    Returns:
        List of anomalies
    """
    anomalies = []
    
    # Extract order quantities from all scenarios
    all_quantities = []
    for scenario in results:
        scenario_id = scenario.get('scenario_id', 0)
        for order in scenario.get('order_history', []):
            all_quantities.append(order.get('quantity', 0))
    
    if not all_quantities:
        return anomalies
    
    # Calculate mean and standard deviation
    mean_quantity = np.mean(all_quantities)
    std_quantity = np.std(all_quantities)
    
    # Detect anomalies
    for scenario in results:
        scenario_id = scenario.get('scenario_id', 0)
        for order in scenario.get('order_history', []):
            quantity = order.get('quantity', 0)
            if abs(quantity - mean_quantity) > threshold * std_quantity:
                anomalies.append({
                    'scenario_id': scenario_id,
                    'day': order.get('day', 0),
                    'quantity': quantity,
                    'mean': mean_quantity,
                    'std': std_quantity,
                    'z_score': (quantity - mean_quantity) / std_quantity
                })
    
    return anomalies

# This function has been removed as it duplicates functionality in SimulationLogger

def log_processing_time(
    start_time: datetime.datetime,
    component: str,
    timing_dict: Dict[str, float],
    logging_level: str = "normal"
) -> None:
    """
    Log processing time for a component and update the timing dictionary.
    
    Args:
        start_time: Start time of the component processing
        component: Name of the component being timed
        timing_dict: Dictionary to update with timing information
        logging_level: Level of logging detail ("off", "minimal", "normal", "detailed")
            - off: No timing information is logged
            - minimal: Only total scenario time is logged
            - normal: Component timing is collected but not printed in real-time
            - detailed: Real-time component timing is printed as components complete
    """
    # Skip timing if logging is off
    if logging_level == "off":
        return
        
    end_time = datetime.datetime.now()
    elapsed_time = (end_time - start_time).total_seconds()
    
    # Update timing dictionary if not in "off" mode
    if component in timing_dict:
        timing_dict[component] += elapsed_time
    else:
        timing_dict[component] = elapsed_time
    
    # Only log detailed timing information if logging_level is "detailed"
    if logging_level == "detailed":
        print(f"  - {component} completed in {elapsed_time:.6f} seconds")


def simulate_inventory(
    params: Dict[str, Any],
    scenario_id: int = 0,
    logger: Optional[SimulationLogger] = None,
    logging_level: str = "normal"
) -> Dict[str, Any]:
    """
    Run a single inventory simulation scenario.
    
    Args:
        params: Simulation parameters
        scenario_id: Scenario ID
        logger: Logger for simulation data
        logging_level: Level of timing detail to log ("off", "minimal", "normal", "detailed")
        
    Returns:
        Dictionary containing simulation results
    """
    # Start timing for this scenario
    scenario_start_time = datetime.datetime.now()
    
    # Initialize timing dictionary to track performance of different parts
    timing = {
        'demand_generation': 0,
        'forecasting': 0,
        'order_processing': 0,
        'inventory_update': 0,
        'reorder_decision': 0,
        'supply_generation': 0
    }
    
    # Extract parameters
    start_inventory = params.get('start_inventory', 100)
    num_periods = params.get('num_periods', 365)
    
    demand_mean = params.get('demand_mean', 10)
    demand_distribution = params.get('demand_distribution', 'normal')
    demand_dispersion_parameter = params.get('demand_dispersion_parameter', 2)
    # Handle both parameter names for backward compatibility
    seasonal_pattern = params.get('seasonal_pattern', params.get('demand_pattern', 'flat'))
    seasonality_weight = params.get('seasonality_weight', 1.0)
    trend_weight = params.get('trend_weight', 0.0)
    trend_monthly_rate = params.get('trend_monthly_rate', 0.01)
    noise_weight = params.get('noise_weight', 1.0)
    
    supply_lt_mean = params.get('supply_lt_mean', 1)
    supply_lt_distribution = params.get('supply_lt_distribution', 'gamma')
    supply_lt_dispersion_parameter = params.get('supply_lt_dispersion_parameter', 0)
    
    reorder_method = params.get('reorder_method', 'onhand_static')
    reorder_point = params.get('reorder_point', 20)
    order_quantity_method = params.get('order_quantity_method', 'fixed')
    reorder_quantity = params.get('reorder_quantity', 50)
    max_quantity = params.get('max_quantity', 100)
    min_days = params.get('min_days', 5)
    max_days = params.get('max_days', 10)
    
    forecast_type = params.get('forecast_type', 'moving_average')
    moving_average_window = params.get('moving_average_window', 30)
    early_period_strategy = params.get('early_period_strategy', 'use_available')
    
    # Initialize simulation state
    current_inventory = start_inventory
    pending_orders = []
    demand_history = []
    forecast_history = []
    inventory_history = [current_inventory]
    dynamic_reorder_points = []
    dynamic_max_quantities = []
    order_history = []
    
    # Initialize additional tracking for logging
    inventory_references = []
    effective_reorder_points = []
    effective_reorder_quantities = []
    placed_order_quantities = []
    received_order_quantities = [0]  # Start with 0 for day 0
    reorder_methods = [reorder_method]  # Start with the method for day 0
    
    # Set initial inventory_reference_day based on policy type
    if reorder_method.startswith("onhand"):
        inventory_reference_days = [0]  # For onhand, start with day 0
    else:
        inventory_reference_days = [int(supply_lt_mean)]  # For projected, start with day supply_lt_mean
    
    # Run simulation for each period
    for day in range(1, num_periods + 1):
        # Time demand generation
        demand_start = datetime.datetime.now()
        
        # Generate demand for the current day
        current_demand = generate_demand(
            demand_mean=demand_mean,
            demand_distribution=demand_distribution,
            demand_dispersion_parameter=demand_dispersion_parameter,
            seasonal_pattern=seasonal_pattern,
            day=day,
            seasonality_weight=seasonality_weight,
            trend_weight=trend_weight,
            trend_monthly_rate=trend_monthly_rate,
            noise_weight=noise_weight,
            num_periods=num_periods
        )
        
        # Add demand to history
        demand_history.append(current_demand)
        
        # Record demand generation time
        log_processing_time(demand_start, 'demand_generation', timing, logging_level)
        
        # Time forecasting
        forecast_start = datetime.datetime.now()
        
        # Generate forecast
        forecast_horizon = int(supply_lt_mean * 1.5)  # Forecast for 1.5x lead time
        if day > 1:  # Skip forecasting on day 1 (no history yet)
            current_forecast = calculate_rolling_forecast(
                history=demand_history,
                forecast_type=forecast_type,
                moving_average_window=moving_average_window,
                forecast_horizon=forecast_horizon,
                early_period_strategy=early_period_strategy
            )
        else:
            current_forecast = [demand_mean] * forecast_horizon
        
        # Add forecast to history
        forecast_history.append(current_forecast)
        
        # Record forecasting time
        log_processing_time(forecast_start, 'forecasting', timing, logging_level)
        
        # Time order processing
        order_proc_start = datetime.datetime.now()
        
        # Process pending orders
        received_supply = process_pending_orders(pending_orders, day)
        
        # Track received supply
        received_order_quantities.append(received_supply)
        
        # Record order processing time
        log_processing_time(order_proc_start, 'order_processing', timing, logging_level)
        
        # Time inventory update
        inv_update_start = datetime.datetime.now()
        
        # Update inventory
        current_inventory = update_inventory(
            current_inventory=current_inventory,
            demand=current_demand,
            received_supply=received_supply
        )
        
        # Add inventory to history
        inventory_history.append(current_inventory)
        
        # Record inventory update time
        log_processing_time(inv_update_start, 'inventory_update', timing, logging_level)
        
        # Time reorder decision
        reorder_start = datetime.datetime.now()
        
        # Calculate inventory reference for reorder decisions
        inventory_reference = calculate_inventory_reference(
            current_inventory=current_inventory,
            pending_orders=pending_orders,
            forecast=current_forecast,
            current_day=day,
            reorder_method=reorder_method,
            supply_lt_mean=supply_lt_mean
        )
        
        # Track inventory reference
        inventory_references.append(inventory_reference)
        
        # Set inventory_reference_day based on policy type
        if reorder_method.startswith("onhand"):
            # For onhand policies, reference day is the current day
            inventory_reference_days.append(day)
        else:
            # For projected policies, reference day is day + supply_lt_mean
            inventory_reference_days.append(day + int(supply_lt_mean))
            
        reorder_methods.append(reorder_method)
        
        # Calculate effective reorder point
        effective_reorder_point = calculate_effective_reorder_point(
            reorder_method=reorder_method,
            reorder_point=reorder_point,
            min_days=min_days,
            forecast=current_forecast
        )
        
        # Track effective reorder point
        effective_reorder_points.append(effective_reorder_point)
        
        # Add dynamic reorder point to history (for backward compatibility)
        dynamic_reorder_points.append(effective_reorder_point)
        
        # Calculate effective reorder quantity
        effective_reorder_quantity = calculate_effective_reorder_quantity(
            order_quantity_method=order_quantity_method,
            reorder_quantity=reorder_quantity,
            max_quantity=max_quantity,
            max_days=max_days,
            inventory_reference=inventory_reference,
            forecast=current_forecast,
            moving_average_window=moving_average_window,
            reorder_method=reorder_method
        )
        
        # Track effective reorder quantity
        effective_reorder_quantities.append(effective_reorder_quantity)
        
        # Calculate effective max quantity for max_quantity method (for backward compatibility)
        if order_quantity_method == 'max_days':
            effective_max_quantity = calculate_effective_reorder_quantity(
                order_quantity_method='max_days',
                reorder_quantity=reorder_quantity,
                max_quantity=max_quantity,
                max_days=max_days,
                inventory_reference=0,  # Not used for calculation
                forecast=current_forecast,
                moving_average_window=moving_average_window,
                reorder_method=reorder_method
            )
        else:
            effective_max_quantity = max_quantity
        
        # Add dynamic max quantity to history (for backward compatibility)
        dynamic_max_quantities.append(effective_max_quantity)
        
        # Record reorder decision time
        log_processing_time(reorder_start, 'reorder_decision', timing, logging_level)
        
        # Time supply generation
        supply_start = datetime.datetime.now()
        
        # Check if reorder is needed
        placed_quantity = 0
        if check_reorder_needed(inventory_reference, effective_reorder_point):
            # Generate supply orders
            new_orders = generate_supply_orders(
                current_day=day,
                inventory_reference=inventory_reference,
                reorder_point=effective_reorder_point,
                order_quantity_method=order_quantity_method,
                supply_lt_mean=supply_lt_mean,
                supply_lt_distribution=supply_lt_distribution,
                supply_lt_dispersion_parameter=supply_lt_dispersion_parameter,
                reorder_quantity=reorder_quantity,
                max_quantity=effective_max_quantity,
                max_days=max_days,
                forecast=current_forecast,
                moving_average_window=moving_average_window,
                reorder_method=reorder_method
            )
            
            # Track placed order quantity
            if new_orders:
                placed_quantity = sum(order['quantity'] for order in new_orders)
            
            # Add new orders to pending orders
            pending_orders.extend(new_orders)
            
            # Add new orders to order history
            order_history.extend(new_orders)
        
        # Track placed order quantity
        placed_order_quantities.append(placed_quantity)
        
        # Record supply generation time
        log_processing_time(supply_start, 'supply_generation', timing, logging_level)
    
    # End timing for this scenario
    scenario_end_time = datetime.datetime.now()
    scenario_duration = (scenario_end_time - scenario_start_time).total_seconds()
    
    # Calculate percentage of time spent in each part
    total_component_time = sum(timing.values())
    timing_percentages = {k: (v / total_component_time * 100) if total_component_time > 0 else 0
                         for k, v in timing.items()}
    
    # Prepare simulation results
    results = {
        'scenario_id': scenario_id,
        'params': params,
        'inventory': inventory_history,
        'demand_history': demand_history,
        'forecast_history': forecast_history,
        'dynamic_reorder_points': dynamic_reorder_points,
        'dynamic_max_quantities': dynamic_max_quantities,
        'order_history': order_history,
        'pending_orders': pending_orders,
        'final_inventory': current_inventory,
        # Add new tracking data
        'inventory_references': inventory_references,
        'effective_reorder_points': effective_reorder_points,
        'effective_reorder_quantities': effective_reorder_quantities,
        'placed_order_quantities': placed_order_quantities,
        'received_order_quantities': received_order_quantities,
        'reorder_methods': reorder_methods,
        'inventory_reference_days': inventory_reference_days,
        # Add timing information
        'scenario_duration': scenario_duration,
        'timing': timing,
        'timing_percentages': timing_percentages
    }
    
    # Log simulation results if logger is provided
    if logger is not None:
        logger.log_simulation_data(results)
    
    # Print detailed timing information for this scenario based on logging level
    if logging_level != "off":
        if logging_level == "minimal":
            print(f"Scenario {scenario_id} completed in {scenario_duration:.4f} seconds")
        else:  # "normal" or "detailed"
            print(f"\nScenario {scenario_id} completed in {scenario_duration:.4f} seconds")
            print(f"  Component timing breakdown:")
            for component, time_spent in sorted(timing.items(), key=lambda x: x[1], reverse=True):
                percentage = timing_percentages[component]
                print(f"  - {component}: {time_spent:.4f}s ({percentage:.1f}%)")
    
    return results

def run_simulation(
    params: Dict[str, Any],
    num_scenarios: Optional[int] = None,
    log_dir: Optional[str] = None,
    logging_level: Union[str, LoggingLevel] = LoggingLevel.LAST_RUN,
    log_format: str = 'csv',
    scenario_sampling: Optional[int] = None,
    period_sampling: Optional[int] = None,
    logger: Optional[SimulationLogger] = None,
    detect_anomalies: bool = False,
    anomaly_threshold: float = 2.0,
    visualize: bool = True,
    insert_to_excel: bool = True,
    output_dir: Optional[str] = None,
    max_scenarios_to_plot: int = 10,
    excel_file: str = None,
    table_name: str = 'InvSim_Parameters',
    enable_scenario_logs: bool = True,
    timing_logging_level: str = "normal"
) -> List[Dict[str, Any]]:
    """
    Run multiple inventory simulation scenarios.
    
    Args:
        params: Simulation parameters
        num_scenarios: Number of scenarios to run
        log_dir: Directory for log files (if None, uses get_logs_dir())
        logging_level: Logging level
        log_format: Log file format
        scenario_sampling: Log every nth scenario
        period_sampling: Log every nth period
        logger: Logger for simulation data
        detect_anomalies: Whether to detect anomalies
        anomaly_threshold: Threshold for anomaly detection
        visualize: Whether to generate visualization plots
        insert_to_excel: Whether to insert dashboard into Excel file
        output_dir: Directory for output plots (if None, uses get_output_dir())
        max_scenarios_to_plot: Maximum number of scenarios to include in plots
        excel_file: Path to Excel file for dashboard insertion
        table_name: Name of table in Excel file
        enable_scenario_logs: Whether to generate scenario log files (default: True)
        timing_logging_level: Level of timing detail to log ("off", "minimal", "normal", "detailed")
        
    Returns:
        List of dictionaries containing simulation results
    """
    # Start timing for all scenarios
    simulation_start_time = datetime.datetime.now()
    
    # Use num_scenarios from params if not provided
    if num_scenarios is None:
        num_scenarios = params.get('num_scenarios', 1)
    
    # Create logger if not provided
    if logger is None:
        if isinstance(logging_level, str):
            logging_level = LoggingLevel[logging_level.upper()]
        
        if logging_level == LoggingLevel.OFF or not enable_scenario_logs:
            logger = NullLogger()
        else:
            # Import path_utils here to avoid circular imports
            from pyps_invsim.utils.path_utils import get_logs_dir
            
            # Use get_logs_dir() if log_dir is not provided
            if log_dir is None:
                log_dir = str(get_logs_dir())
            
            # Create a custom logger that only logs scenario files
            class ScenarioOnlyLogger(SimulationLogger):
                def log_simulation_params(self, params: Dict[str, Any]) -> None:
                    """Skip logging simulation parameters."""
                    pass
                
                def log_aggregated_data(self, data: List[Dict[str, Any]]) -> None:
                    """Skip logging aggregated data."""
                    pass
                
                def log_anomalies(self, anomalies: List[Dict[str, Any]]) -> None:
                    """Skip logging anomalies."""
                    pass
                
                def _log_order_events(self, scenario: Dict[str, Any], scenario_id: int) -> None:
                    """Skip logging order events."""
                    pass
            
            logger = ScenarioOnlyLogger(
                log_dir=log_dir,
                logging_level=logging_level,
                log_format=log_format,
                scenario_sampling=scenario_sampling,
                period_sampling=period_sampling
            )
    
    # Log simulation parameters
    logger.log_simulation_params(params)
    
    # Run simulations
    results = []
    scenarios_start_time = datetime.datetime.now()
    total_scenario_time = 0
    
    for scenario_id in range(num_scenarios):
        scenario_results = simulate_inventory(
            params=params,
            scenario_id=scenario_id,
            logger=logger,
            logging_level=timing_logging_level
        )
        # Add the scenario duration to our total
        total_scenario_time += scenario_results.get('scenario_duration', 0)
        results.append(scenario_results)
    
    scenarios_end_time = datetime.datetime.now()
    scenarios_duration = (scenarios_end_time - scenarios_start_time).total_seconds()
    
    # Log additional results and get aggregated data
    # Extract table_name from params if available
    table_name = params.get('table_name', 'InvSim_Parameters')
    
    # Start timing for post-processing
    post_processing_start_time = datetime.datetime.now()
    
    # Import path_utils here to avoid circular imports
    from pyps_invsim.utils.path_utils import get_output_dir
    
    # Use get_output_dir() if output_dir is not provided
    if output_dir is None:
        output_dir = str(get_output_dir())
    
    log_simulation_results(
        results=results,
        logger=logger,
        params=params,
        detect_anomalies_flag=detect_anomalies,
        anomaly_threshold=anomaly_threshold,
        visualize=visualize,
        insert_to_excel=insert_to_excel,
        output_dir=output_dir,
        max_scenarios_to_plot=max_scenarios_to_plot,
        excel_file=excel_file,
        table_name=table_name,
        enable_scenario_logs=enable_scenario_logs
    )
    
    # End timing for post-processing
    post_processing_end_time = datetime.datetime.now()
    post_processing_duration = (post_processing_end_time - post_processing_start_time).total_seconds()
    
    # End timing for all scenarios
    simulation_end_time = datetime.datetime.now()
    simulation_duration = (simulation_end_time - simulation_start_time).total_seconds()
    
    # Calculate average time per scenario based on actual scenario durations
    avg_scenario_time = total_scenario_time / len(results) if results else 0
    
    # Calculate overhead time (difference between total time and sum of scenario times)
    overhead_time = scenarios_duration - total_scenario_time
    
    # Collect component timing data across all scenarios
    component_timings = {}
    for scenario in results:
        timing_data = scenario.get('timing', {})
        for component, time_spent in timing_data.items():
            if component not in component_timings:
                component_timings[component] = 0
            component_timings[component] += time_spent
    
    # Calculate average and percentage for each component
    total_component_time = sum(component_timings.values()) if component_timings else 0
    avg_component_timings = {k: v / len(results) if results else 0 for k, v in component_timings.items()}
    component_percentages = {k: (v / total_component_time * 100) if total_component_time > 0 else 0
                           for k, v in component_timings.items()}
    
    # Print timing summary based on logging level
    if timing_logging_level != "off":
        if timing_logging_level in ["normal", "detailed"]:
            print(f"\nSimulation Performance Summary:")
            print(f"Total simulation time: {simulation_duration:.4f} seconds")
            print(f"Scenarios execution time: {scenarios_duration:.4f} seconds")
            print(f"Post-processing time: {post_processing_duration:.4f} seconds")
            print(f"Number of scenarios: {len(results)}")
            print(f"Sum of individual scenario times: {total_scenario_time:.4f} seconds")
            print(f"Average time per scenario: {avg_scenario_time:.4f} seconds")
            print(f"Scenario execution overhead: {overhead_time:.4f} seconds")
            
            # Print component timing summary
            if component_timings:
                print(f"\nComponent Timing Summary (across all scenarios):")
                for component, time_spent in sorted(component_timings.items(), key=lambda x: x[1], reverse=True):
                    avg_time = avg_component_timings[component]
                    percentage = component_percentages[component]
                    print(f"  - {component}: {time_spent:.4f}s total, {avg_time:.4f}s avg/scenario ({percentage:.1f}%)")
        elif timing_logging_level == "minimal":
            print(f"\nSimulation completed in {simulation_duration:.4f} seconds ({len(results)} scenarios)")
    
    # Get post-processing timing details if available
    post_processing_timing = {}
    post_processing_percentages = {}
    
    for result in results:
        if 'post_processing_timing' in result:
            post_processing_timing = result['post_processing_timing']
            post_processing_percentages = result['post_processing_percentages']
            break
    
    # Add timing information to the first result for reference
    if results:
        results[0]['total_simulation_duration'] = simulation_duration
        results[0]['scenarios_duration'] = scenarios_duration
        results[0]['post_processing_duration'] = post_processing_duration
        results[0]['post_processing_timing'] = post_processing_timing
        results[0]['post_processing_percentages'] = post_processing_percentages
        results[0]['total_scenario_time'] = total_scenario_time
        results[0]['avg_scenario_time'] = avg_scenario_time
        results[0]['scenario_overhead_time'] = overhead_time
    
    return results

def load_and_run_simulation(
    excel_file: Optional[str] = None,
    table_name: str = 'InvSim_Parameters',
    num_scenarios: Optional[int] = None,
    log_dir: Optional[str] = None,
    logging_level: Union[str, LoggingLevel] = LoggingLevel.LAST_RUN,
    log_format: str = 'csv',
    scenario_sampling: Optional[int] = None,
    period_sampling: Optional[int] = None,
    detect_anomalies: bool = False,
    anomaly_threshold: float = 2.0,
    visualize: bool = True,
    insert_to_excel: bool = True,
    output_dir: Optional[str] = None,
    max_scenarios_to_plot: int = 10,
    enable_scenario_logs: bool = True,
    timing_logging_level: str = "normal"
) -> List[Dict[str, Any]]:
    """
    Load parameters from Excel and run simulation.
    
    Args:
        excel_file: Path to Excel file
        table_name: Name of table in Excel file
        num_scenarios: Number of scenarios to run
        log_dir: Directory for log files (if None, uses get_logs_dir())
        logging_level: Logging level (off, last_run, archive)
        log_format: Log file format (csv, json, pickle)
        scenario_sampling: Log every nth scenario
        period_sampling: Log every nth period
        detect_anomalies: Whether to detect anomalies in simulation data
        anomaly_threshold: Threshold multiplier for anomaly detection
        visualize: Whether to generate visualization plots
        insert_to_excel: Whether to insert dashboard into Excel file
        output_dir: Directory for output plots (if None, uses get_output_dir())
        max_scenarios_to_plot: Maximum number of scenarios to include in plots
        enable_scenario_logs: Whether to generate scenario log files (default: True)
        timing_logging_level: Level of timing detail to log ("off", "minimal", "normal", "detailed")
        
    Returns:
        List of dictionaries containing simulation results
    """
    # Start timing for the entire process
    total_start_time = datetime.datetime.now()
    print(f"Starting simulation at {total_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load parameters using the validated loader (ensures consistency with tests)
    from pyps_invsim.core.parameters import load_simulation_parameters, get_required_parameters
    from pyps_invsim.utils.path_utils import get_invsim_excel_file
    
    # Timing for parameter loading
    param_load_start = datetime.datetime.now()
    
    # If excel_file is not provided, use the utility to find it
    if excel_file is None:
        excel_file = str(get_invsim_excel_file())
    
    params = load_simulation_parameters(
        excel_filepath=excel_file,
        table_name=table_name,
        required_vars=get_required_parameters(),
        use_defaults=True
    )
    
    # End timing for parameter loading
    param_load_end = datetime.datetime.now()
    
    # Run simulation
    results = run_simulation(
        params=params,
        num_scenarios=num_scenarios,
        log_dir=log_dir,
        logging_level=logging_level,
        log_format=log_format,
        scenario_sampling=scenario_sampling,
        period_sampling=period_sampling,
        detect_anomalies=detect_anomalies,
        anomaly_threshold=anomaly_threshold,
        visualize=visualize,
        insert_to_excel=insert_to_excel,
        output_dir=output_dir,
        max_scenarios_to_plot=max_scenarios_to_plot,
        excel_file=excel_file,
        table_name=table_name,
        enable_scenario_logs=enable_scenario_logs,
        timing_logging_level=timing_logging_level
    )
    
    # End timing for the entire process
    total_end_time = datetime.datetime.now()
    total_duration = (total_end_time - total_start_time).total_seconds()
    
    # Calculate parameter loading time
    param_loading_time = (param_load_end - param_load_start).total_seconds()
    
    # Extract timing information from results
    if results and len(results) > 0:
        scenarios_duration = results[0].get('scenarios_duration', 0)
        post_processing_duration = results[0].get('post_processing_duration', 0)
        total_scenario_time = results[0].get('total_scenario_time', 0)
        scenario_overhead = results[0].get('scenario_overhead_time', 0)
        
        # Get post-processing timing details
        post_processing_timing = results[0].get('post_processing_timing', {})
        post_processing_percentages = results[0].get('post_processing_percentages', {})
        
        # Get component timing data
        component_timings = {}
        for scenario in results:
            timing_data = scenario.get('timing', {})
            for component, time_spent in timing_data.items():
                if component not in component_timings:
                    component_timings[component] = 0
                component_timings[component] += time_spent
    else:
        scenarios_duration = 0
        post_processing_duration = 0
        total_scenario_time = 0
        scenario_overhead = 0
        component_timings = {}
        post_processing_timing = {}
        post_processing_percentages = {}
    
    # Calculate other times
    simulation_time = total_duration - param_loading_time
    other_overhead = simulation_time - scenarios_duration - post_processing_duration
    
    # Calculate component percentages
    total_component_time = sum(component_timings.values()) if component_timings else 0
    component_percentages = {k: (v / total_duration * 100) if total_duration > 0 else 0
                           for k, v in component_timings.items()}
    
    # Print overall timing summary
    print(f"\n===== OVERALL PERFORMANCE SUMMARY =====")
    print(f"Total execution time: {total_duration:.4f} seconds (100%)")
    print(f"  ├─ Parameter loading: {param_loading_time:.4f} seconds ({param_loading_time/total_duration*100:.1f}%)")
    print(f"  └─ Simulation execution: {simulation_time:.4f} seconds ({simulation_time/total_duration*100:.1f}%)")
    print(f"     ├─ Scenarios execution: {scenarios_duration:.4f} seconds ({scenarios_duration/total_duration*100:.1f}%)")
    print(f"     │  ├─ Actual scenario processing: {total_scenario_time:.4f} seconds ({total_scenario_time/total_duration*100:.1f}%)")
    print(f"     │  └─ Scenario overhead: {scenario_overhead:.4f} seconds ({scenario_overhead/total_duration*100:.1f}%)")
    print(f"     ├─ Post-processing: {post_processing_duration:.4f} seconds ({post_processing_duration/total_duration*100:.1f}%)")
    print(f"     └─ Other overhead: {other_overhead:.4f} seconds ({other_overhead/total_duration*100:.1f}%)")
    
    # Print post-processing timing breakdown
    if post_processing_timing:
        print(f"\nPost-processing Timing Breakdown:")
        for component, time_spent in sorted(post_processing_timing.items(), key=lambda x: x[1], reverse=True):
            percentage = post_processing_percentages[component]
            print(f"  - {component}: {time_spent:.4f}s ({percentage:.1f}% of post-processing)")
    
    # Print component timing breakdown
    if component_timings:
        print(f"\nComponent Timing Breakdown:")
        for component, time_spent in sorted(component_timings.items(), key=lambda x: x[1], reverse=True):
            percentage = component_percentages[component]
            print(f"  - {component}: {time_spent:.4f}s ({percentage:.1f}% of total time)")
    
    print(f"\nCompleted at {total_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=======================================")
    
    return results

def prepare_simulation_csv_data(
    results: List[Dict[str, Any]],
    simulation_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Prepare simulation data for CSV export.
    
    Args:
        results: List of simulation results
        simulation_id: Simulation ID
        
    Returns:
        List of dictionaries containing CSV data
    """
    csv_data = []
    
    for scenario in results:
        scenario_id = scenario.get('scenario_id', 0)
        inventory = scenario.get('inventory', [])
        
        # Calculate minimum and average inventory levels
        min_inventory = min(inventory) if inventory else 0
        avg_inventory = sum(inventory) / len(inventory) if inventory else 0
        
        # Count stock-out days
        stock_out_days = sum(1 for inv in inventory if inv <= 0)
        
        # Create CSV data
        row = {
            'SimulationID': simulation_id if simulation_id else '',
            'ScenarioNum': scenario_id,
            'MinimumInventoryLevel': min_inventory,
            'AverageInventoryLevel': avg_inventory,
            'NumberStockOutDays': stock_out_days
        }
        
        csv_data.append(row)
    
    return csv_data

def prepare_parameters_csv_data(
    params: Dict[str, Any],
    simulation_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Prepare parameters for CSV export.
    
    Args:
        params: Simulation parameters
        simulation_id: Simulation ID
        
    Returns:
        List of dictionaries containing CSV data
    """
    csv_data = []
    
    for key, value in params.items():
        row = {
            'SimulationID': simulation_id if simulation_id else '',
            'ParameterName': key,
            'ParameterValue': value
        }
        csv_data.append(row)
    
    return csv_data

def log_simulation_results(
    results: List[Dict[str, Any]],
    logger: SimulationLogger,
    params: Dict[str, Any],
    detect_anomalies_flag: bool = False,
    anomaly_threshold: float = 2.0,
    visualize: bool = True,
    insert_to_excel: bool = True,
    output_dir: str = 'src/pyps_invsim/outputs',
    max_scenarios_to_plot: int = 10,
    excel_file: str = None,
    table_name: str = 'InvSim_Parameters',
    enable_scenario_logs: bool = True
) -> Dict[str, Any]:
    """
    Log simulation results and return aggregated data.
    
    Args:
        results: List of simulation results
        logger: Logger for simulation data
        params: Simulation parameters
        detect_anomalies_flag: Whether to detect anomalies
        anomaly_threshold: Threshold for anomaly detection
        visualize: Whether to generate visualization plots
        insert_to_excel: Whether to insert dashboard into Excel file
        output_dir: Directory for output plots
        max_scenarios_to_plot: Maximum number of scenarios to include in plots
        excel_file: Path to Excel file for dashboard insertion
        table_name: Name of table in Excel file
        enable_scenario_logs: Whether to generate scenario log files (default: True)
        
    Returns:
        Dictionary containing aggregated results
    """
    # Initialize timing dictionary for post-processing
    post_processing_timing = {
        'logging': 0,
        'data_extraction': 0,
        'lead_time_generation': 0,
        'visualization': 0,
        'dashboard_generation': 0,
        'excel_insertion': 0,
        'results_file_generation': 0
    }
    
    # Start timing for logging
    logging_start = datetime.datetime.now()
    
    # Log simulation data
    logger.log_simulation_data(results)
    
    # Log aggregated data
    logger.log_aggregated_data(results)
    
    # Detect anomalies if requested
    if detect_anomalies_flag:
        anomalies = detect_anomalies(results, anomaly_threshold)
        logger.log_anomalies(anomalies)
    
    # End timing for logging
    logging_end = datetime.datetime.now()
    post_processing_timing['logging'] = (logging_end - logging_start).total_seconds()
    
    # Start timing for data extraction
    data_extraction_start = datetime.datetime.now()
    
    # Extract data for return value
    all_scenarios = []
    all_demands = []
    all_forecasts = []
    all_dynamic_reorder_points = []
    all_dynamic_max_quantities = []
    min_levels = []
    avg_levels = []
    
    for scenario in results:
        inventory = scenario.get('inventory', [])
        demand_history = scenario.get('demand_history', [])
        forecast_history = scenario.get('forecast_history', [])
        dynamic_reorder_points = scenario.get('dynamic_reorder_points', [])
        dynamic_max_quantities = scenario.get('dynamic_max_quantities', [])
        
        all_scenarios.append(inventory)
        all_demands.append(demand_history)
        
        # Extract first forecast value from each forecast
        first_forecasts = []
        for forecast in forecast_history:
            if isinstance(forecast, list) and forecast:
                first_forecasts.append(forecast[0])
            elif isinstance(forecast, (int, float)):
                first_forecasts.append(forecast)
        
        all_forecasts.append(first_forecasts)
        all_dynamic_reorder_points.append(dynamic_reorder_points)
        all_dynamic_max_quantities.append(dynamic_max_quantities)
        
        # Calculate minimum and average inventory levels
        min_levels.append(min(inventory) if inventory else 0)
        avg_levels.append(sum(inventory) / len(inventory) if inventory else 0)
    
    # End timing for data extraction
    data_extraction_end = datetime.datetime.now()
    post_processing_timing['data_extraction'] = (data_extraction_end - data_extraction_start).total_seconds()
    
    # Start timing for lead time generation
    lead_time_start = datetime.datetime.now()
    
    # Generate lead times for analysis
    lead_times = []
    supply_lt_mean = params.get('supply_lt_mean', 5)
    supply_lt_distribution = params.get('supply_lt_distribution', 'normal')
    supply_lt_dispersion_parameter = params.get('supply_lt_dispersion_parameter', 1)
    
    for _ in range(10000):  # Generate a large sample
        lead_time = generate_lead_time(
            supply_lt_mean=supply_lt_mean,
            supply_lt_distribution=supply_lt_distribution,
            supply_lt_dispersion_parameter=supply_lt_dispersion_parameter
        )
        lead_times.append(lead_time)
    
    # End timing for lead time generation
    lead_time_end = datetime.datetime.now()
    post_processing_timing['lead_time_generation'] = (lead_time_end - lead_time_start).total_seconds()
    
    # Visualization
    if visualize:
        # Start timing for visualization
        visualization_start = datetime.datetime.now()
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate and save the dashboard only
        from pyps_invsim.visualization.dashboard import save_dashboard
        
        # Start timing for dashboard generation
        dashboard_start = datetime.datetime.now()
        
        dashboard_path = save_dashboard(
            all_scenarios=all_scenarios,
            all_demands=all_demands,
            min_levels=min_levels,
            avg_levels=avg_levels,
            lead_times=lead_times,
            params=params,
            output_dir=output_dir,
            filename="inventory_dashboard.png"
        )
        
        # End timing for dashboard generation
        dashboard_end = datetime.datetime.now()
        post_processing_timing['dashboard_generation'] = (dashboard_end - dashboard_start).total_seconds()
        
        print(f"Dashboard saved to: {dashboard_path}")
        
        # Insert dashboard into Excel if requested
        if insert_to_excel:
            # Start timing for Excel insertion
            excel_start = datetime.datetime.now()
            
            # Try to use xlwings to insert the figure directly
            try:
                import xlwings as xw
                import matplotlib.pyplot as plt
                
                # Try to connect to an already open workbook first
                try:
                    wb = xw.books[os.path.basename(excel_file)]
                    print(f"Connected to already open workbook: {os.path.basename(excel_file)}")
                except:
                    # If not open, open it
                    wb = xw.Book(excel_file)
                    print(f"Opened workbook: {excel_file}")
                
                # Check if the sheet exists, create it if not
                try:
                    sheet = wb.sheets["InvSim_Dashboard"]
                    print(f"Using existing sheet: InvSim_Dashboard")
                except:
                    sheet = wb.sheets.add("InvSim_Dashboard")
                    print(f"Created new sheet: InvSim_Dashboard")
                
                # Clear the sheet
                sheet.clear()
                
                # Add a title
                sheet.range("A1").value = "Inventory Simulation Dashboard"
                sheet.range("A1").font.size = 16
                sheet.range("A1").font.bold = True
                
                # Get the figure from the visualization module
                from pyps_invsim.visualization.dashboard import create_inventory_dashboard
                
                # Create the dashboard figure
                fig = create_inventory_dashboard(
                    all_scenarios=all_scenarios,
                    all_demands=all_demands,
                    min_levels=min_levels,
                    avg_levels=avg_levels,
                    lead_times=lead_times,
                    params=params,
                    max_scenarios=len(all_scenarios)  # Use all available scenarios
                )
                
                # Insert the figure into Excel
                sheet.pictures.add(
                    fig,
                    name="InvSimDashboard",
                    update=True,
                    left=sheet.range("A3").left,
                    top=sheet.range("A3").top,
                    width=900,
                    height=700
                )
                
                # Save the workbook
                wb.save()
                print(f"Dashboard inserted into Excel file using xlwings: {excel_file}")
                
                # Close the figure to free memory
                plt.close(fig)
                
                success = True
                
            except Exception as e:
                print(f"Error using xlwings for dashboard insertion: {e}")
                # Fall back to the old method
                from pyps_invsim.utils.excel_dashboard import insert_dashboard_image_to_excel
                
                success = insert_dashboard_image_to_excel(
                    excel_file=excel_file,
                    image_path=dashboard_path,
                    table_name=table_name
                )
                
                if success:
                    print(f"Dashboard inserted into Excel file using VBScript: {excel_file}")
                else:
                    print(f"Failed to insert dashboard into Excel file: {excel_file}")
            
            # End timing for Excel insertion
            excel_end = datetime.datetime.now()
            post_processing_timing['excel_insertion'] = (excel_end - excel_start).total_seconds()
        
        # End timing for visualization
        visualization_end = datetime.datetime.now()
        post_processing_timing['visualization'] = (visualization_end - visualization_start).total_seconds()
    
    # Start timing for results file generation
    results_file_start = datetime.datetime.now()
    
    # Save simulation results to file
    moving_average_window = params.get('moving_average_window', 30)
    results_file = save_simulation_results_to_file(
        results=results,
        params=params,
        moving_average_window=moving_average_window
    )
    
    # End timing for results file generation
    results_file_end = datetime.datetime.now()
    post_processing_timing['results_file_generation'] = (results_file_end - results_file_start).total_seconds()
    
    # Calculate total post-processing time
    total_post_processing_time = sum(post_processing_timing.values())
    
    # Calculate percentages
    post_processing_percentages = {
        k: (v / total_post_processing_time * 100) if total_post_processing_time > 0 else 0
        for k, v in post_processing_timing.items()
    }
    
    # Print detailed post-processing timing information
    print(f"\nPost-processing timing breakdown:")
    for component, time_spent in sorted(post_processing_timing.items(), key=lambda x: x[1], reverse=True):
        percentage = post_processing_percentages[component]
        print(f"  - {component}: {time_spent:.4f}s ({percentage:.1f}%)")
    
    # Return the data
    return {
        'all_scenarios': all_scenarios,
        'all_demands': all_demands,
        'all_forecasts': all_forecasts,
        'all_dynamic_reorder_points': all_dynamic_reorder_points,
        'all_dynamic_max_quantities': all_dynamic_max_quantities,
        'min_levels': min_levels,
        'avg_levels': avg_levels,
        'lead_times': lead_times,
        'results_file': results_file,
        'post_processing_timing': post_processing_timing,
        'post_processing_percentages': post_processing_percentages
    }

# Function removed as requested

def save_simulation_results_to_file(
    results: List[Dict[str, Any]],
    params: Dict[str, Any],
    moving_average_window: int = 30,
    output_dir: Optional[str] = None
) -> str:
    """
    Save simulation results to a CSV file with detailed statistics.
    
    Args:
        results: List of simulation results
        params: Simulation parameters
        moving_average_window: Window size for moving average calculation
        output_dir: Directory to save the results file (if None, uses data/results)
        
    Returns:
        Path to the saved file
    """
    import os
    import csv
    import numpy as np
    from datetime import datetime
    
    # Import path_utils here to avoid circular imports
    from pyps_invsim.utils.path_utils import get_data_dir
    
    # Use data/results directory if output_dir is not provided
    if output_dir is None:
        data_dir = get_data_dir()
        output_dir = str(data_dir / 'results')
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%y%m%d%H%M")
    filename = f"InvSim_Results_{timestamp}.csv"
    filepath = os.path.join(output_dir, filename)
    
    # Extract all scenarios and demands
    all_scenarios = []
    all_demands = []
    
    for scenario in results:
        inventory = scenario.get('inventory', [])
        demand_history = scenario.get('demand_history', [])
        all_scenarios.append(inventory)
        all_demands.append(demand_history)
    
    # Import utility functions for inventory calculations
    from pyps_invsim.utils.inventory_utils import (
        calculate_inventory_days_for_scenarios,
        calculate_inventory_statistics,
        calculate_stockout_days_for_scenarios,
        calculate_stockout_statistics
    )
    
    # Calculate inventory days using the utility function
    inventory_days_per_scenario = calculate_inventory_days_for_scenarios(
        all_scenarios=all_scenarios,
        all_demands=all_demands,
        moving_average_window=moving_average_window
    )
    
    # Calculate stockout days using the utility function
    stockout_days_per_scenario = calculate_stockout_days_for_scenarios(
        all_scenarios=all_scenarios
    )
    
    # Calculate inventory statistics
    inventory_stats = calculate_inventory_statistics(inventory_days_per_scenario)
    median_inventory_days = inventory_stats['median']
    percentile_95_inventory_days = inventory_stats['percentile_95']
    q75_inventory_days = inventory_stats['q75']
    q25_inventory_days = inventory_stats['q25']
    iqr_inventory_days = inventory_stats['iqr']
    
    # Calculate stockout statistics
    stockout_stats = calculate_stockout_statistics(stockout_days_per_scenario)
    
    # Calculate average stockout days
    avg_stockout_days = round(sum(stockout_days_per_scenario) / len(stockout_days_per_scenario), 2) if stockout_days_per_scenario else 0.0
    
    # Get other stockout statistics
    percentile_95_stockout_days = stockout_stats['percentile_95']
    q75_stockout_days = stockout_stats['q75']
    q25_stockout_days = stockout_stats['q25']
    iqr_stockout_days = stockout_stats['iqr']
    
    # Get all default parameters
    from pyps_invsim.utils.config_utils import load_default_parameters
    from pyps_invsim.utils.path_utils import get_config_dir
    
    config_dir = get_config_dir()
    config_filepath = str(config_dir / 'default_parameters.yaml')
    default_params = load_default_parameters(config_filepath)
    
    # Merge default parameters with provided parameters
    all_params = {**default_params, **params}
    
    # Prepare data for CSV
    data = {
        # Add all parameters
        **all_params,
        
        # Add calculated statistics
        'Median_Average_Inventory_Days': median_inventory_days,
        '95th_Percentile_Average_Inventory_Days': percentile_95_inventory_days,
        'IQR_Average_Inventory_Days': iqr_inventory_days,
        'Avg_Stockout_Days': avg_stockout_days,
        '95th_Percentile_Stockout_Days': percentile_95_stockout_days,
        'IQR_Stockout_Days': iqr_stockout_days
    }
    
    # Use pandas for better CSV handling
    import pandas as pd
    
    # Round all float values in the data dictionary
    formatted_data = {}
    for key, value in data.items():
        if isinstance(value, float):
            formatted_data[key] = round(value, 2)
        else:
            formatted_data[key] = value
    
    # Convert data to a pandas DataFrame
    df = pd.DataFrame([formatted_data])
    
    # Write to CSV file
    df.to_csv(filepath, index=False)
    
    print(f"Simulation results saved to: {filepath}")
    return filepath

if __name__ == "__main__":
    import argparse
    from pyps_invsim.utils.path_utils import get_excel_dir, get_logs_dir, get_output_dir
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Run inventory simulation')
    parser.add_argument('--excel_file', type=str, default=str(get_invsim_excel_file()), help='Path to Excel file')
    parser.add_argument('--table_name', type=str, default='InvSim_Parameters', help='Name of table in Excel file')
    parser.add_argument('--num_scenarios', type=int, help='Number of scenarios to run')
    parser.add_argument('--log_dir', type=str, help='Directory for log files (default: auto-detected)')
    parser.add_argument('--logging_level', type=str, choices=['off', 'last_run', 'archive'], default='last_run', help='Logging level')
    parser.add_argument('--log_format', type=str, choices=['csv', 'json', 'pickle'], default='csv', help='Log file format')
    parser.add_argument('--scenario_sampling', type=int, help='Log every nth scenario')
    parser.add_argument('--period_sampling', type=int, help='Log every nth period')
    parser.add_argument('--detect_anomalies', action='store_true', help='Detect anomalies in simulation data')
    parser.add_argument('--anomaly_threshold', type=float, default=2.0, help='Threshold multiplier for anomaly detection')
    parser.add_argument('--visualize', action='store_true', default=True, help='Generate visualization plots')
    parser.add_argument('--insert_to_excel', action='store_true', default=True, help='Insert dashboard into Excel file')
    parser.add_argument('--output_dir', type=str, help='Directory for output plots (default: auto-detected)')
    parser.add_argument('--max_scenarios_to_plot', type=int, default=10, help='Maximum number of scenarios to include in plots')
    parser.add_argument('--timing_logging_level', type=str, choices=['off', 'minimal', 'normal', 'detailed'],
                        default='minimal', help='Level of timing detail to log')
    
    args = parser.parse_args()
    
    # Run simulation
    results = load_and_run_simulation(
        excel_file=args.excel_file,
        table_name=args.table_name,
        num_scenarios=args.num_scenarios,
        log_dir=args.log_dir,
        logging_level=args.logging_level,
        log_format=args.log_format,
        scenario_sampling=args.scenario_sampling,
        period_sampling=args.period_sampling,
        detect_anomalies=args.detect_anomalies,
        anomaly_threshold=args.anomaly_threshold,
        visualize=args.visualize,
        insert_to_excel=args.insert_to_excel,
        output_dir=args.output_dir,
        max_scenarios_to_plot=args.max_scenarios_to_plot,
        timing_logging_level=args.timing_logging_level
    )
    
    # Generate and save the dashboard
    from pyps_invsim.visualization.dashboard import save_dashboard
    
    # Use get_output_dir() if output_dir is not provided
    output_dir = args.output_dir if args.output_dir else str(get_output_dir())
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Dashboard generation and Excel insertion are handled in load_and_run_simulation
    
    # Visualization is now handled inside the load_and_run_simulation function
    print(f"Simulation completed with {len(results)} scenarios.")
