# Inventory Simulation Visualization

This module provides visualization tools for the inventory simulation results.

## Dashboard Visualization

The `dashboard.py` module implements the visualization requirements specified in `docs/visualization_requirements.md`. It creates a comprehensive dashboard with 7 charts arranged in 3 rows:

1. **Inventory Performance across all scenarios** (Row 1, columns 1-5)
   - Shows inventory levels across all scenarios
   - Axes cross at zero

2. **Average Monthly Demand across all scenarios** (Row 2, columns 1-5)
   - Shows light grey lines for the average monthly demand for each scenario
   - Axes cross at zero

3. **Minimum Inventory Histogram** (Row 3, column 1)
   - Shows the distribution of minimum inventory values
   - Includes dotted red lines for 5th and 95th percentiles

4. **Average Inventory Histogram** (Row 3, column 2)
   - Shows the distribution of average inventory values
   - Includes dotted red lines for 5th and 95th percentiles

5. **Daily Demand Histogram** (Row 3, column 3)
   - Shows the distribution of daily demand quantities
   - Includes a dotted green line for the mean

6. **Supply Lead-Time Histogram** (Row 3, column 4)
   - Shows the distribution of supply lead times
   - Includes a dotted green line for the mean

7. **Parameters and Metrics Table** (Row 3, column 5)
   - Displays key simulation parameters
   - Shows service level and stockout metrics

## Usage

### From Python Code

```python
from pyps_invsim.visualization.dashboard import create_inventory_dashboard, save_dashboard

# Create and save the dashboard
output_path = save_dashboard(
    all_scenarios=all_scenarios,
    all_demands=all_demands,
    min_levels=min_levels,
    avg_levels=avg_levels,
    lead_times=lead_times,
    params=params,
    output_dir="src/pyps_invsim/outputs",
    filename="inventory_dashboard.png"
)
```

### From Command Line

Use the provided script to generate the dashboard:

```bash
python scripts/generate_dashboard.py --num_scenarios 100
```

Options:
- `--excel_file`: Path to Excel file with parameters
- `--table_name`: Name of table in Excel file
- `--num_scenarios`: Number of scenarios to run
- `--log_dir`: Directory for log files
- `--output_dir`: Directory for output files
- `--filename`: Filename for the dashboard image

## Integration with Simulation

The dashboard visualization is designed to work with the output of the `level1_inventory_simulation.py` module. It extracts the necessary data from the simulation results to create the visualizations.

## Output

All visualization outputs are saved to the `src/pyps_invsim/outputs` directory by default.