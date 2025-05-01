"""
Basic example of running an inventory simulation with PyPS InvSim.
"""
import os
import sys
import yaml
from pathlib import Path

try:
    # Try importing directly (works when package is installed)
    from pyps_invsim.simulations import run_inventory_simulation
    from pyps_invsim.utils.config_utils import load_simulation_parameters
    from pyps_invsim.utils.path_utils import get_config_dir
except ImportError:
    # If that fails, try adding the parent directory to the path
    # (works when running from the source directory)
    parent_dir = str(Path(__file__).parent.parent.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    # Now try importing again
    from pyps_invsim.simulations import run_inventory_simulation
    from pyps_invsim.utils.config_utils import load_simulation_parameters
    from pyps_invsim.utils.path_utils import get_config_dir

def main():
    """Run a basic inventory simulation."""
    # Load default parameters
    config_dir = get_config_dir()
    default_params_file = os.path.join(config_dir, "default_parameters.yaml")
    
    # If the default parameters file doesn't exist, create a simple one
    if not os.path.exists(default_params_file):
        # Create the config directory if it doesn't exist
        os.makedirs(config_dir, exist_ok=True)
        
        # Create a simple parameters file
        params = {
            "simulation": {
                "num_periods": 365,
                "num_scenarios": 1,
                "random_seed": 42
            },
            "inventory": {
                "initial_inventory": 100,
                "reorder_point": 50,
                "order_quantity": 100,
                "max_inventory": 200
            },
            "demand": {
                "mean": 10,
                "std_dev": 2,
                "seasonality": False,
                "trend": False
            },
            "supply": {
                "lead_time_mean": 7,
                "lead_time_std_dev": 1
            }
        }
        
        # Write the parameters to the file
        with open(default_params_file, "w") as f:
            yaml.dump(params, f, default_flow_style=False)
        
        print(f"Created default parameters file at {default_params_file}")
    
    # Load the parameters
    params = load_simulation_parameters(default_params_file)
    
    # Run the simulation
    results = run_inventory_simulation(params)
    
    # Calculate summary statistics from the results
    # The results are a list of scenario results
    avg_inventory_levels = []
    service_levels = []
    num_orders_list = []
    total_demand_list = []
    
    for scenario in results:
        # Extract inventory levels
        inventory_levels = [period.get('inventory_level', 0) for period in scenario.get('periods', [])]
        avg_inventory_level = sum(inventory_levels) / len(inventory_levels) if inventory_levels else 0
        avg_inventory_levels.append(avg_inventory_level)
        
        # Extract service level
        stockouts = sum(1 for period in scenario.get('periods', []) if period.get('stockout', False))
        total_periods = len(scenario.get('periods', []))
        service_level = 1 - (stockouts / total_periods) if total_periods > 0 else 0
        service_levels.append(service_level)
        
        # Extract number of orders
        num_orders = len(scenario.get('order_history', []))
        num_orders_list.append(num_orders)
        
        # Extract total demand
        total_demand = sum(period.get('demand', 0) for period in scenario.get('periods', []))
        total_demand_list.append(total_demand)
    
    # Calculate averages across all scenarios
    avg_inventory_level = sum(avg_inventory_levels) / len(avg_inventory_levels) if avg_inventory_levels else 0
    avg_service_level = sum(service_levels) / len(service_levels) if service_levels else 0
    avg_num_orders = sum(num_orders_list) / len(num_orders_list) if num_orders_list else 0
    avg_total_demand = sum(total_demand_list) / len(total_demand_list) if total_demand_list else 0
    
    # Print summary results
    print("\nSimulation Results (averaged across all scenarios):")
    print(f"Average Inventory Level: {avg_inventory_level:.2f}")
    print(f"Service Level: {avg_service_level:.2%}")
    print(f"Average Number of Orders: {avg_num_orders:.2f}")
    print(f"Average Total Demand: {avg_total_demand:.2f}")
    
    return results

if __name__ == "__main__":
    main()