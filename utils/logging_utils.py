"""
Logging utilities for inventory simulations.
"""
import os
import csv
import json
import pickle
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Literal
import pandas as pd
import numpy as np
from datetime import datetime

class LoggingLevel(Enum):
    """Logging levels for inventory simulations."""
    OFF = 0      # No logging
    LAST_RUN = 1 # Log only the last run
    ARCHIVE = 2  # Log all runs with timestamps

class NullLogger:
    """
    A logger that does nothing.
    
    This class implements the same interface as SimulationLogger but does nothing.
    It's used when logging is disabled to avoid conditionals in the simulation code.
    """
    
    def log_simulation_params(self, params: Dict[str, Any]) -> None:
        """Do nothing."""
        pass
    
    def log_simulation_data(
        self,
        scenario_data: List[Dict[str, Any]],
        scenario_ids: Optional[List[int]] = None
    ) -> None:
        """Do nothing."""
        pass
    
    def log_aggregated_data(
        self,
        data: Dict[str, Any],
        include_percentiles: bool = True
    ) -> None:
        """Do nothing."""
        pass
    
    def log_order_events(
        self,
        order_events: List[Dict[str, Any]],
        scenario_id: Optional[int] = None
    ) -> None:
        """Do nothing."""
        pass
    
    def log_anomalies(
        self,
        anomalies: List[Dict[str, Any]]
    ) -> None:
        """Do nothing."""
        pass

class SimulationLogger:
    """
    Logger for inventory simulations.
    
    This class provides methods to log simulation data at different levels of detail
    and with different storage options.
    """
    
    def __init__(
        self,
        log_dir: Union[str, Path] = "logs",
        logging_level: LoggingLevel = LoggingLevel.LAST_RUN,
        log_format: Literal["csv", "json", "pickle"] = "csv",
        scenario_sampling: Optional[int] = None,
        period_sampling: Optional[int] = None
    ):
        """
        Initialize the simulation logger.
        
        Args:
            log_dir: Directory to store log files
            logging_level: Level of logging detail
            log_format: Format to store log data
            scenario_sampling: If provided, only log every nth scenario
            period_sampling: If provided, only log every nth period
        """
        self.log_dir = Path(log_dir)
        self.logging_level = logging_level
        self.log_format = log_format
        self.scenario_sampling = scenario_sampling
        self.period_sampling = period_sampling
        
        # Create log directory if it doesn't exist
        if self.logging_level != LoggingLevel.OFF:
            self.log_dir.mkdir(exist_ok=True, parents=True)
    
    def _round_numeric_values(self, data):
        """
        Round all numeric values in the data to 2 decimal places.
        
        Args:
            data: Data to round (can be a scalar, list, dict, or nested structure)
            
        Returns:
            Data with all numeric values rounded to 2 decimal places
        """
        if isinstance(data, (int, float)):
            return round(data, 2)
        elif isinstance(data, list):
            return [self._round_numeric_values(item) for item in data]
        elif isinstance(data, dict):
            return {key: self._round_numeric_values(value) for key, value in data.items()}
        else:
            return data
    
    def log_simulation_params(self, params: Dict[str, Any]) -> None:
        """
        Log simulation parameters.
        
        Args:
            params: Dictionary of simulation parameters
        """
        if self.logging_level == LoggingLevel.OFF:
            return
        
        # Round numeric values
        params = self._round_numeric_values(params)
        
        # Create timestamp for archive mode
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Determine filename based on logging level
        if self.logging_level == LoggingLevel.LAST_RUN:
            filename = self.log_dir / f"simulation_params.{self.log_format}"
        else:  # ARCHIVE
            filename = self.log_dir / f"simulation_params_{timestamp}.{self.log_format}"
        
        # Write parameters to file
        if self.log_format == "csv":
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Parameter", "Value"])
                for key, value in params.items():
                    writer.writerow([key, value])
        
        elif self.log_format == "json":
            with open(filename, 'w') as f:
                json.dump(params, f, indent=2)
        
        elif self.log_format == "pickle":
            with open(filename, 'wb') as f:
                pickle.dump(params, f)
    
    def log_simulation_data(
        self,
        scenario_data: List[Dict[str, Any]],
        scenario_ids: Optional[List[int]] = None
    ) -> None:
        """
        Log detailed simulation data for each scenario.
        
        Args:
            scenario_data: List of dictionaries containing data for each scenario
            scenario_ids: Optional list of scenario IDs (defaults to sequential numbering)
        """
        if self.logging_level == LoggingLevel.OFF:
            return
        
        # Create timestamp for archive mode
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Apply scenario sampling if specified
        if self.scenario_sampling is not None:
            if scenario_ids is None:
                scenario_ids = list(range(len(scenario_data)))
            
            sampled_indices = list(range(0, len(scenario_data), self.scenario_sampling))
            scenario_data = [scenario_data[i] for i in sampled_indices]
            scenario_ids = [scenario_ids[i] for i in sampled_indices]
        
        # Process each scenario
        for i, data in enumerate(scenario_data):
            scenario_id = scenario_ids[i] if scenario_ids else i
            
            # Round numeric values
            data = self._round_numeric_values(data)
            
            # Apply period sampling if specified
            if self.period_sampling is not None:
                for key in data:
                    if isinstance(data[key], list) and len(data[key]) > self.period_sampling:
                        data[key] = data[key][::self.period_sampling]
            
            # Determine filename based on logging level
            if self.logging_level == LoggingLevel.LAST_RUN:
                filename = self.log_dir / f"scenario_{scenario_id}.{self.log_format}"
            else:  # ARCHIVE
                filename = self.log_dir / f"scenario_{scenario_id}_{timestamp}.{self.log_format}"
            
            # Write data to file
            if self.log_format == "csv":
                # Convert to DataFrame for easier CSV writing
                df_data = {}
                max_length = 0
                
                # Find the maximum length of any list in the data
                for key, value in data.items():
                    if isinstance(value, list):
                        max_length = max(max_length, len(value))
                
                # Prepare data for DataFrame
                for key, value in data.items():
                    if isinstance(value, list):
                        df_data[key] = value + [None] * (max_length - len(value))
                    else:
                        df_data[key] = [value] + [None] * (max_length - 1)
                
                # Create and save DataFrame
                pd.DataFrame(df_data).to_csv(filename, index=False)
            
            elif self.log_format == "json":
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
            
            elif self.log_format == "pickle":
                with open(filename, 'wb') as f:
                    pickle.dump(data, f)
    
    def log_aggregated_data(
        self,
        data: Dict[str, Any],
        include_percentiles: bool = True
    ) -> None:
        """
        Log aggregated simulation data across all scenarios.
        
        Args:
            data: Dictionary of aggregated data
            include_percentiles: Whether to include percentile calculations
        """
        if self.logging_level == LoggingLevel.OFF:
            return
        
        # Create timestamp for archive mode
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create a copy of the data to avoid modifying the original
        data_copy = data.copy()
        
        # Round numeric values
        data_copy = self._round_numeric_values(data_copy)
        
        # Calculate percentiles if requested
        if include_percentiles:
            percentiles_data = {}
            
            for key, value in data_copy.items():
                if isinstance(value, list) and all(isinstance(x, list) for x in value):
                    # This is a list of lists (e.g., all_scenarios)
                    # Calculate percentiles across scenarios for each period
                    periods = min(len(x) for x in value)
                    percentiles = {
                        "5th": [],
                        "25th": [],
                        "50th": [],
                        "75th": [],
                        "95th": []
                    }
                    
                    for period in range(periods):
                        period_values = [x[period] for x in value if period < len(x)]
                        percentiles["5th"].append(round(np.percentile(period_values, 5), 2))
                        percentiles["25th"].append(round(np.percentile(period_values, 25), 2))
                        percentiles["50th"].append(round(np.percentile(period_values, 50), 2))
                        percentiles["75th"].append(round(np.percentile(period_values, 75), 2))
                        percentiles["95th"].append(round(np.percentile(period_values, 95), 2))
                    
                    percentiles_data[f"{key}_percentiles"] = percentiles
            
            # Add percentiles to the data copy
            data_copy.update(percentiles_data)
        
        # Determine filename based on logging level
        if self.logging_level == LoggingLevel.LAST_RUN:
            filename = self.log_dir / f"aggregated_data.{self.log_format}"
        else:  # ARCHIVE
            filename = self.log_dir / f"aggregated_data_{timestamp}.{self.log_format}"
        
        # Write data to file
        if self.log_format == "csv":
            # For CSV, we'll save each key as a separate file to avoid issues with different array lengths
            for key, value in data_copy.items():
                # Skip complex nested structures that are hard to represent in CSV
                if isinstance(value, list) and all(isinstance(x, list) for x in value):
                    continue
                
                # Create a separate file for each key
                key_filename = self.log_dir / f"aggregated_{key}.{self.log_format}"
                
                # Convert to DataFrame if possible
                try:
                    if isinstance(value, dict):
                        # Convert dict to DataFrame
                        df = pd.DataFrame(value)
                    elif isinstance(value, list):
                        # Convert list to DataFrame
                        df = pd.DataFrame({key: value})
                    else:
                        # Convert scalar to DataFrame
                        df = pd.DataFrame({key: [value]})
                    
                    # Save DataFrame to CSV
                    df.to_csv(key_filename, index=False)
                except Exception as e:
                    print(f"Warning: Could not save {key} to CSV: {e}")
        
        elif self.log_format == "json":
            with open(filename, 'w') as f:
                json.dump(data_copy, f, indent=2)
        
        elif self.log_format == "pickle":
            with open(filename, 'wb') as f:
                pickle.dump(data_copy, f)
    
    def log_order_events(
        self,
        order_events: List[Dict[str, Any]],
        scenario_id: Optional[int] = None
    ) -> None:
        """
        Log order events for a specific scenario.
        
        Args:
            order_events: List of order event dictionaries
            scenario_id: Optional scenario ID (defaults to 'unknown')
        """
        if self.logging_level == LoggingLevel.OFF:
            return
        
        if not order_events:
            return
        
        # Round numeric values
        order_events = self._round_numeric_values(order_events)
        
        # Create timestamp for archive mode
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Determine filename based on logging level
        scenario_str = str(scenario_id) if scenario_id is not None else "unknown"
        
        if self.logging_level == LoggingLevel.LAST_RUN:
            filename = self.log_dir / f"order_events_scenario_{scenario_str}.{self.log_format}"
        else:  # ARCHIVE
            filename = self.log_dir / f"order_events_scenario_{scenario_str}_{timestamp}.{self.log_format}"
        
        # Write data to file
        if self.log_format == "csv":
            # Get all possible keys
            all_keys = set()
            for event in order_events:
                all_keys.update(event.keys())
            
            with open(filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
                writer.writeheader()
                writer.writerows(order_events)
        
        elif self.log_format == "json":
            with open(filename, 'w') as f:
                json.dump(order_events, f, indent=2)
        
        elif self.log_format == "pickle":
            with open(filename, 'wb') as f:
                pickle.dump(order_events, f)
    
    def log_anomalies(
        self,
        anomalies: List[Dict[str, Any]]
    ) -> None:
        """
        Log anomalies detected during simulation.
        
        Args:
            anomalies: List of anomaly dictionaries
        """
        if self.logging_level == LoggingLevel.OFF:
            return
        
        if not anomalies:
            return
        
        # Round numeric values
        anomalies = self._round_numeric_values(anomalies)
        
        # Create timestamp for archive mode
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Determine filename based on logging level
        if self.logging_level == LoggingLevel.LAST_RUN:
            filename = self.log_dir / f"anomalies.{self.log_format}"
        else:  # ARCHIVE
            filename = self.log_dir / f"anomalies_{timestamp}.{self.log_format}"
        
        # Write data to file
        if self.log_format == "csv":
            # Get all possible keys
            all_keys = set()
            for anomaly in anomalies:
                all_keys.update(anomaly.keys())
            
            with open(filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
                writer.writeheader()
                writer.writerows(anomalies)
        
        elif self.log_format == "json":
            with open(filename, 'w') as f:
                json.dump(anomalies, f, indent=2)
        
        elif self.log_format == "pickle":
            with open(filename, 'wb') as f:
                pickle.dump(anomalies, f)

def detect_anomalies(
    scenario_data: List[Dict[str, Any]],
    threshold_multiplier: float = 2.0,
    min_threshold: float = 100.0
) -> List[Dict[str, Any]]:
    """
    Detect anomalies in simulation data.
    
    Args:
        scenario_data: List of dictionaries containing data for each scenario
        threshold_multiplier: Multiplier for standard deviation to determine threshold
        min_threshold: Minimum threshold for anomaly detection
    
    Returns:
        List of anomaly dictionaries
    """
    anomalies = []
    
    # Extract order quantities from all scenarios
    all_order_quantities = []
    for i, data in enumerate(scenario_data):
        if "order_history" in data:
            for order in data["order_history"]:
                all_order_quantities.append(order["quantity"])
    
    if not all_order_quantities:
        return anomalies
    
    # Calculate statistics
    mean_qty = np.mean(all_order_quantities)
    std_qty = np.std(all_order_quantities)
    
    # Determine threshold
    threshold = max(min_threshold, mean_qty + threshold_multiplier * std_qty)
    
    # Detect anomalies
    for i, data in enumerate(scenario_data):
        if "order_history" in data:
            for order in data["order_history"]:
                if order["quantity"] > threshold:
                    anomaly = {
                        "scenario_id": i,
                        "day": order["day"],
                        "quantity": round(order["quantity"], 2),
                        "threshold": round(threshold, 2),
                        "mean_qty": round(mean_qty, 2),
                        "std_qty": round(std_qty, 2),
                        "z_score": round((order["quantity"] - mean_qty) / std_qty if std_qty > 0 else float('inf'), 2)
                    }
                    
                    # Add context if available
                    if "inventory" in order:
                        anomaly["inventory"] = round(order["inventory"], 2)
                    
                    if "demand" in order:
                        anomaly["demand"] = round(order["demand"], 2)
                    
                    if "forecast" in order:
                        anomaly["forecast"] = round(order["forecast"], 2)
                    
                    if "dynamic_max_quantity" in order:
                        anomaly["dynamic_max_quantity"] = round(order["dynamic_max_quantity"], 2)
                    
                    if "dynamic_reorder_point" in order:
                        anomaly["dynamic_reorder_point"] = round(order["dynamic_reorder_point"], 2)
                    
                    anomalies.append(anomaly)
    
    return anomalies