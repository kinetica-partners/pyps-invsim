"""
Simulation logger for inventory simulations.
"""
import os
import csv
import json
import pickle
import datetime
import numpy as np
from enum import Enum
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

class LoggingLevel(Enum):
    """Logging level for simulation logger."""
    OFF = 0
    LAST_RUN = 1
    ARCHIVE = 2

class NullLogger:
    """Null logger that does nothing."""
    
    def log_simulation_params(self, params: Dict[str, Any]) -> None:
        """Log simulation parameters."""
        pass
    
    def log_simulation_data(self, data: Dict[str, Any]) -> None:
        """Log simulation data."""
        pass
    
    def log_aggregated_data(self, data: List[Dict[str, Any]]) -> None:
        """Log aggregated data."""
        pass
    
    def log_anomalies(self, anomalies: List[Dict[str, Any]]) -> None:
        """Log anomalies."""
        pass

class SimulationLogger:
    """Logger for inventory simulation."""
    
    def __init__(
        self,
        log_dir: str = 'logs',
        logging_level: LoggingLevel = LoggingLevel.LAST_RUN,
        log_format: str = 'csv',
        scenario_sampling: Optional[int] = None,
        period_sampling: Optional[int] = None
    ):
        """
        Initialize simulation logger.
        
        Args:
            log_dir: Directory for log files
            logging_level: Logging level
            log_format: Log file format
            scenario_sampling: Log every nth scenario
            period_sampling: Log every nth period
        """
        self.log_dir = Path(log_dir)
        self.logging_level = logging_level
        self.log_format = log_format
        self.scenario_sampling = scenario_sampling
        self.period_sampling = period_sampling
        
        # Create log directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Generate timestamp for archive mode
        self.timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def _get_filename(self, base_name: str) -> Path:
        """
        Get filename for log file.
        
        Args:
            base_name: Base name for log file
            
        Returns:
            Path to log file
        """
        if self.logging_level == LoggingLevel.ARCHIVE:
            return self.log_dir / f"{base_name}_{self.timestamp}.{self.log_format}"
        else:
            return self.log_dir / f"{base_name}.{self.log_format}"
    
    def _round_numeric_values(
        self,
        data: Dict[str, Any],
        precision: int = 2
    ) -> Dict[str, Any]:
        """
        Round numeric values in a dictionary.
        
        Args:
            data: Dictionary containing data
            precision: Precision for rounding
            
        Returns:
            Dictionary with rounded numeric values
        """
        rounded_data = {}
        
        for key, value in data.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                rounded_data[key] = round(value, precision)
            elif isinstance(value, dict):
                rounded_data[key] = self._round_numeric_values(value, precision)
            elif isinstance(value, list):
                rounded_data[key] = [
                    self._round_numeric_values(item, precision) if isinstance(item, dict)
                    else round(item, precision) if isinstance(item, (int, float)) and not isinstance(item, bool)
                    else item
                    for item in value
                ]
            else:
                rounded_data[key] = value
        
        return rounded_data
    
    def log_simulation_params(self, params: Dict[str, Any]) -> None:
        """
        Log simulation parameters.
        
        Args:
            params: Simulation parameters
        """
        if self.logging_level == LoggingLevel.OFF:
            return
        
        # Round numeric values
        rounded_params = self._round_numeric_values(params)
        
        # Get filename
        filename = self._get_filename('simulation_params')
        
        # Log parameters based on format
        if self.log_format == 'csv':
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Parameter', 'Value'])
                for key, value in rounded_params.items():
                    writer.writerow([key, value])
        
        elif self.log_format == 'json':
            with open(filename, 'w') as f:
                json.dump(rounded_params, f, indent=2)
        
        elif self.log_format == 'pickle':
            with open(filename, 'wb') as f:
                pickle.dump(rounded_params, f)
    
    def log_simulation_data(self, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> None:
        """
        Log simulation data.
        
        Args:
            data: Simulation data
        """
        if self.logging_level == LoggingLevel.OFF:
            return
        
        # Handle single scenario or list of scenarios
        if isinstance(data, dict):
            scenarios = [data]
        else:
            scenarios = data
        
        # Log each scenario
        for scenario in scenarios:
            # Check scenario sampling
            scenario_id = scenario.get('scenario_id', 0)
            if self.scenario_sampling is not None and scenario_id % self.scenario_sampling != 0:
                continue
            
            # Round numeric values
            rounded_scenario = self._round_numeric_values(scenario)
            
            # Get filename
            filename = self._get_filename(f'scenario_{scenario_id}')
            
            # Log scenario based on format
            if self.log_format == 'csv':
                self._log_scenario_to_csv(rounded_scenario, filename)
            
            elif self.log_format == 'json':
                with open(filename, 'w') as f:
                    json.dump(rounded_scenario, f, indent=2)
            
            elif self.log_format == 'pickle':
                with open(filename, 'wb') as f:
                    pickle.dump(rounded_scenario, f)
            
            # Log order events
            self._log_order_events(rounded_scenario, scenario_id)
    
    def _log_scenario_to_csv(self, scenario: Dict[str, Any], filename: Path) -> None:
        """
        Log scenario to CSV file.
        
        Args:
            scenario: Scenario data
            filename: Path to CSV file
        """
        # Extract data
        inventory = scenario.get('inventory', [])
        demand_history = scenario.get('demand_history', [])
        forecast_history = scenario.get('forecast_history', [])
        dynamic_reorder_points = scenario.get('dynamic_reorder_points', [])
        dynamic_max_quantities = scenario.get('dynamic_max_quantities', [])
        
        # Ensure all lists have the same length
        max_length = max(
            len(inventory),
            len(demand_history) + 1,  # +1 because inventory includes starting inventory
            len(forecast_history) + 1,
            len(dynamic_reorder_points) + 1,
            len(dynamic_max_quantities) + 1
        )
        
        # Pad lists if necessary
        inventory = inventory + [None] * (max_length - len(inventory))
        demand_history = [None] + demand_history + [None] * (max_length - len(demand_history) - 1)
        
        # Handle forecast history (list of lists)
        padded_forecast = [None]
        for forecast in forecast_history:
            if isinstance(forecast, list):
                padded_forecast.append(forecast[0] if forecast else None)
            else:
                padded_forecast.append(forecast)
        padded_forecast = padded_forecast + [None] * (max_length - len(padded_forecast))
        
        dynamic_reorder_points = [None] + dynamic_reorder_points + [None] * (max_length - len(dynamic_reorder_points) - 1)
        dynamic_max_quantities = [None] + dynamic_max_quantities + [None] * (max_length - len(dynamic_max_quantities) - 1)
        
        # Extract additional data
        inventory_references = scenario.get('inventory_references', [])
        effective_reorder_points = scenario.get('effective_reorder_points', [])
        effective_reorder_quantities = scenario.get('effective_reorder_quantities', [])
        placed_order_quantities = scenario.get('placed_order_quantities', [])
        received_order_quantities = scenario.get('received_order_quantities', [])
        reorder_methods = scenario.get('reorder_methods', [])
        inventory_reference_days = scenario.get('inventory_reference_days', [])
        
        # Pad additional lists if necessary
        inventory_references = inventory_references + [None] * (max_length - len(inventory_references))
        effective_reorder_points = effective_reorder_points + [None] * (max_length - len(effective_reorder_points))
        effective_reorder_quantities = effective_reorder_quantities + [None] * (max_length - len(effective_reorder_quantities))
        placed_order_quantities = placed_order_quantities + [None] * (max_length - len(placed_order_quantities))
        received_order_quantities = received_order_quantities + [None] * (max_length - len(received_order_quantities))
        reorder_methods = reorder_methods + [None] * (max_length - len(reorder_methods))
        inventory_reference_days = inventory_reference_days + [None] * (max_length - len(inventory_reference_days))
        
        # Write CSV file
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'day',
                'current_inventory',
                'demand',
                'reorder_method',
                'inventory_reference_day',
                'inventory_reference',
                'effective_reorder_point',
                'effective_reorder_quantity',
                'placed_order_quantity',
                'received_order_quantity',
                'forecast'
            ])
            
            for i in range(max_length):
                # Check period sampling
                if self.period_sampling is not None and i % self.period_sampling != 0:
                    continue
                
                writer.writerow([
                    i,
                    inventory[i],
                    demand_history[i],
                    reorder_methods[i],
                    inventory_reference_days[i],
                    inventory_references[i],
                    effective_reorder_points[i],
                    effective_reorder_quantities[i],
                    placed_order_quantities[i],
                    received_order_quantities[i],
                    padded_forecast[i]
                ])
    
    def _log_order_events(self, scenario: Dict[str, Any], scenario_id: int) -> None:
        """
        Log order events.
        
        Args:
            scenario: Scenario data
            scenario_id: Scenario ID
        """
        order_history = scenario.get('order_history', [])
        
        if not order_history:
            return
        
        # Get filename
        filename = self._get_filename(f'order_events_scenario_{scenario_id}')
        
        # Log order events based on format
        if self.log_format == 'csv':
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Day', 'Quantity', 'LeadTime', 'DueDate'])
                
                for order in order_history:
                    writer.writerow([
                        order.get('day', 0),
                        order.get('quantity', 0),
                        order.get('lead_time', 0),
                        order.get('due_date', 0)
                    ])
        
        elif self.log_format == 'json':
            with open(filename, 'w') as f:
                json.dump(order_history, f, indent=2)
        
        elif self.log_format == 'pickle':
            with open(filename, 'wb') as f:
                pickle.dump(order_history, f)
    
    def log_aggregated_data(self, results: List[Dict[str, Any]]) -> None:
        """
        Log aggregated data.
        
        Args:
            results: List of simulation results
        """
        if self.logging_level == LoggingLevel.OFF:
            return
        
        # Aggregate inventory levels
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
        
        # Calculate percentiles for all scenarios
        self._log_percentiles(all_scenarios, 'aggregated_all_scenarios_percentiles')
        
        # Calculate percentiles for all demands
        self._log_percentiles(all_demands, 'aggregated_all_demands_percentiles')
        
        # Calculate percentiles for all forecasts
        self._log_percentiles(all_forecasts, 'aggregated_all_forecasts_percentiles')
        
        # Calculate percentiles for all dynamic reorder points
        self._log_percentiles(all_dynamic_reorder_points, 'aggregated_all_dynamic_reorder_points_percentiles')
        
        # Calculate percentiles for all dynamic max quantities
        self._log_percentiles(all_dynamic_max_quantities, 'aggregated_all_dynamic_max_quantities_percentiles')
        
        # Log minimum levels
        self._log_simple_list(min_levels, 'aggregated_min_levels')
        
        # Log average levels
        self._log_simple_list(avg_levels, 'aggregated_avg_levels')
        
        # Generate lead times for analysis
        params = results[0].get('params', {})
        supply_lt_mean = params.get('supply_lt_mean', 5)
        supply_lt_distribution = params.get('supply_lt_distribution', 'normal')
        supply_lt_dispersion_parameter = params.get('supply_lt_dispersion_parameter', 1)
        
        lead_times = []
        for _ in range(10000):  # Generate a large sample
            lead_time = self._generate_lead_time(
                supply_lt_mean=supply_lt_mean,
                supply_lt_distribution=supply_lt_distribution,
                supply_lt_dispersion_parameter=supply_lt_dispersion_parameter
            )
            lead_times.append(lead_time)
        
        # Log lead times
        self._log_simple_list(lead_times, 'aggregated_lead_times')
    
    def _generate_lead_time(
        self,
        supply_lt_mean: float,
        supply_lt_distribution: str,
        supply_lt_dispersion_parameter: float
    ) -> int:
        """
        Generate a lead time.
        
        Args:
            supply_lt_mean: Mean lead time
            supply_lt_distribution: Distribution for lead time
            supply_lt_dispersion_parameter: Dispersion parameter for lead time
            
        Returns:
            Lead time
        """
        if supply_lt_distribution == 'normal':
            lead_time = np.random.normal(supply_lt_mean, supply_lt_dispersion_parameter)
            lead_time = max(1, round(lead_time))  # Ensure lead time is at least 1
        
        elif supply_lt_distribution == 'poisson':
            lead_time = np.random.poisson(supply_lt_mean)
            lead_time = max(1, lead_time)  # Ensure lead time is at least 1
        
        elif supply_lt_distribution == 'gamma':
            # Handle the case where dispersion parameter is 0 (no randomness)
            if supply_lt_dispersion_parameter == 0:
                lead_time = supply_lt_mean
            else:
                shape = supply_lt_mean ** 2 / supply_lt_dispersion_parameter ** 2
                scale = supply_lt_dispersion_parameter ** 2 / supply_lt_mean
                lead_time = np.random.gamma(shape, scale)
            lead_time = max(1, round(lead_time))  # Ensure lead time is at least 1
        
        elif supply_lt_distribution == 'lognormal':
            mu = np.log(supply_lt_mean ** 2 / np.sqrt(supply_lt_mean ** 2 + supply_lt_dispersion_parameter ** 2))
            sigma = np.sqrt(np.log(1 + (supply_lt_dispersion_parameter ** 2 / supply_lt_mean ** 2)))
            lead_time = np.random.lognormal(mu, sigma)
            lead_time = max(1, round(lead_time))  # Ensure lead time is at least 1
        
        else:
            raise ValueError(f"Invalid supply_lt_distribution: {supply_lt_distribution}")
        
        return lead_time
    
    def _log_percentiles(self, data: List[List[float]], filename_base: str) -> None:
        """
        Log percentiles of data.
        
        Args:
            data: List of lists of data
            filename_base: Base filename
        """
        # Calculate percentiles
        percentiles = [5, 10, 25, 50, 75, 90, 95]
        
        # Transpose data to get values for each day
        transposed = list(zip(*data))
        
        # Calculate percentiles for each day
        percentile_data = []
        for day, values in enumerate(transposed):
            row = {'Day': day}
            
            for p in percentiles:
                row[f'P{p}'] = np.percentile(values, p)
            
            percentile_data.append(row)
        
        # Get filename
        filename = self._get_filename(filename_base)
        
        # Log percentiles based on format
        if self.log_format == 'csv':
            with open(filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['Day'] + [f'P{p}' for p in percentiles])
                writer.writeheader()
                writer.writerows(percentile_data)
        
        elif self.log_format == 'json':
            with open(filename, 'w') as f:
                json.dump(percentile_data, f, indent=2)
        
        elif self.log_format == 'pickle':
            with open(filename, 'wb') as f:
                pickle.dump(percentile_data, f)
    
    def _log_simple_list(self, data: List[float], filename_base: str) -> None:
        """
        Log a simple list of data.
        
        Args:
            data: List of data
            filename_base: Base filename
        """
        # Get filename
        filename = self._get_filename(filename_base)
        
        # Log data based on format
        if self.log_format == 'csv':
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Value'])
                for value in data:
                    writer.writerow([value])
        
        elif self.log_format == 'json':
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
        
        elif self.log_format == 'pickle':
            with open(filename, 'wb') as f:
                pickle.dump(data, f)
    
    def log_anomalies(self, anomalies: List[Dict[str, Any]]) -> None:
        """
        Log anomalies.
        
        Args:
            anomalies: List of anomalies
        """
        if self.logging_level == LoggingLevel.OFF or not anomalies:
            return
        
        # Round numeric values
        rounded_anomalies = [self._round_numeric_values(anomaly) for anomaly in anomalies]
        
        # Get filename
        filename = self._get_filename('anomalies')
        
        # Log anomalies based on format
        if self.log_format == 'csv':
            with open(filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=rounded_anomalies[0].keys())
                writer.writeheader()
                writer.writerows(rounded_anomalies)
        
        elif self.log_format == 'json':
            with open(filename, 'w') as f:
                json.dump(rounded_anomalies, f, indent=2)
        
        elif self.log_format == 'pickle':
            with open(filename, 'wb') as f:
                pickle.dump(rounded_anomalies, f)