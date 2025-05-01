"""
IMPORTANT: This file is a teaching example to show progression in the simulation development.
DO NOT MODIFY THIS FILE - it is intentionally kept in its original form.
For the latest implementation, see level1_inventory_simulation.py.
"""
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import gamma
from pathlib import Path
import os
import openpyxl
from typing import Dict, Any, Optional, List

# Define required variables
required_vars = [
    'start_inventory', 'demand_mean', 'demand_dispersion_parameter', 'reorder_point',
    'reorder_quantity', 'supply_lt_mean', 'supply_lt_dispersion_parameter',
    'num_periods', 'num_scenarios'
]

def load_parameters_from_excel(excel_path: Path, required_vars: List[str]) -> Dict[str, Any]:
    """
    Load parameters from an Excel file.
    
    Args:
        excel_path: Path to the Excel file
        required_vars: List of parameter names to find
        
    Returns:
        Dictionary of parameter values
    """
    found_params = {}
    
    try:
        # Load the Excel workbook
        wb = openpyxl.load_workbook(str(excel_path), data_only=True)
        
        # First, try to find the InvSim_Parameters sheet directly
        if 'InvSim_Parameters' in wb.sheetnames:
            sheet = wb['InvSim_Parameters']
            
            # Look for a table with VariableName and VariableValue columns
            var_name_col = None
            var_value_col = None
            
            # Find the header row
            for row in range(1, min(20, sheet.max_row + 1)):
                for col in range(1, min(10, sheet.max_column + 1)):
                    cell_value = sheet.cell(row=row, column=col).value
                    if cell_value == 'VariableName':
                        var_name_col = col
                    elif cell_value == 'VariableValue':
                        var_value_col = col
                
                # If we found both columns, process the data
                if var_name_col is not None and var_value_col is not None:
                    # Start from the next row after headers
                    for r in range(row + 1, sheet.max_row + 1):
                        name = sheet.cell(row=r, column=var_name_col).value
                        value = sheet.cell(row=r, column=var_value_col).value
                        
                        if name and isinstance(name, str):
                            # Clean up the parameter name (remove trailing spaces)
                            name = name.strip()
                            
                            # Convert string values to numbers if needed
                            if isinstance(value, str):
                                if value.isdigit():
                                    value = int(value)
                                elif value.replace('.', '', 1).isdigit():
                                    value = float(value)
                            
                            found_params[name] = value
                    
                    break  # Stop looking after finding and processing the table
        
        # If we couldn't find the parameters in the InvSim_Parameters sheet,
        # try looking in other sheets
        if not found_params:
            for sheet_name in wb.sheetnames:
                sheet = wb[sheet_name]
                
                # Look for parameters in this sheet
                for row in range(1, sheet.max_row + 1):
                    for col in range(1, sheet.max_column + 1):
                        cell_value = sheet.cell(row=row, column=col).value
                        
                        # If this cell contains a parameter name
                        if cell_value and isinstance(cell_value, str) and cell_value.strip() in required_vars:
                            param_name = cell_value.strip()
                            
                            # Try to find the value in the cell to the right
                            if col < sheet.max_column:
                                value_cell = sheet.cell(row=row, column=col + 1).value
                                if value_cell is not None:
                                    # Convert string values to numbers if needed
                                    if isinstance(value_cell, str):
                                        if value_cell.isdigit():
                                            value_cell = int(value_cell)
                                        elif value_cell.replace('.', '', 1).isdigit():
                                            value_cell = float(value_cell)
                                    found_params[param_name] = value_cell
                            
                            # If not found to the right, try the cell below
                            elif row < sheet.max_row and param_name not in found_params:
                                value_cell = sheet.cell(row=row + 1, column=col).value
                                if value_cell is not None:
                                    # Convert string values to numbers if needed
                                    if isinstance(value_cell, str):
                                        if value_cell.isdigit():
                                            value_cell = int(value_cell)
                                        elif value_cell.replace('.', '', 1).isdigit():
                                            value_cell = float(value_cell)
                                    found_params[param_name] = value_cell
    
    except Exception as e:
        print(f"Error loading Excel file {excel_path}: {e}")
    
    return found_params

def find_parameters_in_excel(required_vars: List[str]) -> Dict[str, Any]:
    """
    Find parameters in Excel from multiple possible sources:
    1. Specific file paths
    2. Current workbook when running in Excel (Python in Excel)
    3. Current workbook when running with xlwings
    
    Args:
        required_vars: List of parameter names to find
        
    Returns:
        Dictionary of parameter values
    """
    # Default parameters as a fallback
    default_params = {
        'start_inventory': 250,
        'demand_mean': 5,
        'demand_dispersion_parameter': 2.5,
        'reorder_point': 500,
        'reorder_quantity': 150,
        'supply_lt_mean': 15,
        'supply_lt_dispersion_parameter': 5,
        'num_periods': 365,
        'num_scenarios': 100
    }
    
    # List of possible Excel file paths to check
    possible_paths = [
        Path('src/pyps_invsim/data/excel/PyPS_InvSim_v0.1.0.xlsm'),
        Path('data/excel/PyPS_InvSim_v0.1.0.xlsm'),
        Path('excel/PyPS_InvSim_v0.1.0.xlsm'),
        Path('../excel/PyPS_InvSim_v0.1.0.xlsm'),
        Path('../../excel/PyPS_InvSim_v0.1.0.xlsm'),
    ]
    
    # Try to get the current workbook if running in Excel (Python in Excel)
    try:
        import pythoncom
        from win32com.client import Dispatch
        
        # Get Excel application
        xl_app = Dispatch("Excel.Application")
        if xl_app.ActiveWorkbook:
            # We're running inside Excel
            print("Running inside Excel (Python in Excel)")
            current_wb_path = Path(xl_app.ActiveWorkbook.FullName)
            possible_paths.insert(0, current_wb_path)
    except (ImportError, Exception):
        pass
    
    # Try to get the current workbook if running with xlwings
    try:
        import xlwings as xw
        
        # Check if we're running in an Excel context
        if xw.books:
            # We're running with xlwings
            print("Running with xlwings")
            active_book = xw.books.active
            if active_book:
                current_wb_path = Path(active_book.fullname)
                possible_paths.insert(0, current_wb_path)
    except (ImportError, Exception):
        pass
    
    # Try each possible path
    for path in possible_paths:
        try:
            if path.exists():
                print(f"Trying to load parameters from: {path}")
                params = load_parameters_from_excel(path, required_vars)
                if params and all(var in params for var in required_vars):
                    print(f"Successfully loaded parameters from: {path}")
                    return params
        except Exception as e:
            print(f"Error loading from {path}: {e}")
    
    # If we get here, we couldn't find parameters in any of the Excel files
    print("Could not find parameters in any Excel file. Using default values.")
    return default_params

# Find parameters from Excel
params = find_parameters_in_excel(required_vars)

# Print found parameters for debugging
print("Found parameters:")
for key, value in params.items():
    print(f"  {key}: {value}")

# Extract parameters
start_inventory = params['start_inventory']
demand_mean = params['demand_mean']
demand_dispersion_parameter = params['demand_dispersion_parameter']
reorder_point = params['reorder_point']
reorder_quantity = params['reorder_quantity']
supply_lt_mean = params['supply_lt_mean']
supply_lt_dispersion_parameter = params['supply_lt_dispersion_parameter']
num_periods = params['num_periods']
num_scenarios = params['num_scenarios']

# Ensure num_scenarios is at least 1
if num_scenarios <= 0:
    print(f"Warning: num_scenarios is {num_scenarios}, but should be positive.")
    print(f"Using default value of 100 instead.")
    num_scenarios = 100

# Function to simulate inventory levels (unchanged)
def simulate_inventory(start_inv, demand_mean, demand_dispersion_parameter, reorder_point, reorder_qty, supply_lt_mean):
    inventory = [start_inv]
    pending_orders = []
    
    for day in range(1, num_periods):
        # Process pending orders
        for order in pending_orders:
            if order['arrival'] == day:
                inventory.append(inventory[-1] + order['quantity'])
                pending_orders.remove(order)
                break
        else:
            inventory.append(inventory[-1])
        
        # Generate daily demand
        demand = max(0, np.random.normal(demand_mean, demand_dispersion_parameter))
        inventory[-1] = max(0, inventory[-1] - demand)
        
        # Check reorder point
        if inventory[-1] <= reorder_point and not pending_orders:
            lt = int(gamma.rvs(supply_lt_dispersion_parameter, scale=supply_lt_mean/supply_lt_dispersion_parameter))
            pending_orders.append({'arrival': day + lt, 'quantity': reorder_qty})
    
    return inventory

# Run simulations
all_scenarios = [simulate_inventory(start_inventory, demand_mean, demand_dispersion_parameter, 
                                   reorder_point, reorder_quantity, supply_lt_mean) 
                 for _ in range(num_scenarios)]

# Calculate statistics
min_levels = [min(scenario) for scenario in all_scenarios]
avg_levels = [np.mean(scenario) for scenario in all_scenarios]

# Generate daily demands and lead times for histograms
daily_demands = [max(0, np.random.normal(demand_mean, demand_dispersion_parameter)) for _ in range(10000)]
lead_times = [int(gamma.rvs(supply_lt_dispersion_parameter, scale=supply_lt_mean/supply_lt_dispersion_parameter)) for _ in range(10000)]

# Plotting
plt.figure(figsize=(15, 12))

# Random walk plot
plt.subplot(2, 1, 1)
for scenario in all_scenarios[:100]:  # Plot first 100 scenarios for clarity
    plt.plot(scenario)
plt.title('Inventory Level Random Walk')
plt.xlabel('Period')
plt.ylabel('Inventory Level')

# Function to add percentile lines to histogram
def add_percentile_lines(ax, data):
    percentile_5 = np.percentile(data, 5)
    percentile_95 = np.percentile(data, 95)
    ax.axvline(percentile_5, color='red', linestyle=':', label='5th percentile')
    ax.axvline(percentile_95, color='red', linestyle=':', label='95th percentile')
    ax.legend()

# Histograms
plt.subplot(2, 4, 5)
plt.hist(min_levels, bins=30)
plt.title('Minimum Inventory Level')
add_percentile_lines(plt.gca(), min_levels)

plt.subplot(2, 4, 6)
plt.hist(avg_levels, bins=30)
plt.title('Average Inventory Level')
add_percentile_lines(plt.gca(), avg_levels)

plt.subplot(2, 4, 7)
plt.hist(daily_demands, bins=30)
plt.title('Daily Demand')
add_percentile_lines(plt.gca(), daily_demands)

plt.subplot(2, 4, 8)
plt.hist(lead_times, bins=range(min(lead_times), max(lead_times) + 2, 1))
plt.title('Lead Time Distribution')
add_percentile_lines(plt.gca(), lead_times)

plt.tight_layout()
plt.show()