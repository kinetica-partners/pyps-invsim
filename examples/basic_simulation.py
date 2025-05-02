"""
Example script for running a basic simulation.

This script demonstrates how to use the PyPS-InvSim package in different environments:
1. When running as an installed package
2. When running from src/pyps_invsim directly
3. When running from the development project
"""
import os
import sys
from pathlib import Path

# Add the parent directory to the path
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent

# Try to import the import helper
try:
    # If running from the package
    from pyps_invsim.utils.import_helper import setup_imports
    setup_imports()
except ImportError:
    # If running from the source directory
    sys.path.insert(0, str(parent_dir))
    from pyps_invsim.utils.import_helper import setup_imports
    setup_imports()

# Now import the rest of the modules
from pyps_invsim.simulations.level1_inventory_simulation import run_simulation
from pyps_invsim.utils.path_utils import get_data_dir, get_config_dir, get_logs_dir
from pyps_invsim.logging.simulation_logger import LoggingLevel

def main():
    """Run a basic inventory simulation."""
    print("PyPS-InvSim Basic Simulation Example")
    print("====================================")
    
    # Print the paths to demonstrate they work in all environments
    print(f"Config directory: {get_config_dir()}")
    print(f"Logs directory: {get_logs_dir()}")
    print(f"Data directory: {get_data_dir()}")
    print(f"Sample directory: {get_data_dir('sample')}")
    
    # Load parameters from the default config file
    config_dir = get_config_dir()
    config_file = config_dir / "default_parameters.yaml"
    
    if config_file.exists():
        print(f"Using configuration from: {config_file}")
    else:
        print(f"Configuration file not found: {config_file}")
        print("Using default parameters")
    
    # Run a simple simulation
    print("\nRunning simulation...")
    # Create a parameters dictionary
    simulation_params = {
        'num_periods': 26,
        'start_inventory': 100,
        'reorder_point': 20,
        'reorder_quantity': 50
    }
    
    # Run the simulation
    results = run_simulation(
        params=simulation_params,
        num_scenarios=1,
        logging_level=LoggingLevel.LAST_RUN
    )
    
    # Process and print some results
    print("\nSimulation Results:")
    
    # Extract data from the first scenario
    if results and len(results) > 0:
        scenario = results[0]
        
        # Calculate average inventory
        inventory_history = scenario.get('inventory', [])
        avg_inventory = sum(inventory_history) / len(inventory_history) if inventory_history else 0
        
        # Calculate service level (percentage of periods without stockout)
        stockouts = sum(1 for inv in inventory_history if inv <= 0)
        service_level = 1.0 - (stockouts / len(inventory_history)) if inventory_history else 0
        
        # Print results
        print(f"Average inventory level: {avg_inventory:.2f}")
        print(f"Service level: {service_level:.2%}")
        print(f"Final inventory: {scenario.get('final_inventory', 0)}")
        
        # Print timing information
        timing = scenario.get('timing', {})
        if timing:
            print("\nTiming Information:")
            for component, time_spent in timing.items():
                print(f"  {component}: {time_spent:.4f}s")
    else:
        print("No simulation results available.")
    
    # Save results to logs directory
    logs_dir = get_logs_dir()
    print(f"\nResults saved to: {logs_dir}")

if __name__ == "__main__":
    main()