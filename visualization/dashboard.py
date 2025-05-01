"""
Dashboard visualization for inventory simulations.

This module provides functions to create a comprehensive dashboard
of simulation results according to the visualization requirements.
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from typing import List, Dict, Any, Optional, Tuple, Union
import os
from pathlib import Path

def create_inventory_dashboard(
    all_scenarios: List[List[float]],
    all_demands: List[List[float]],
    min_levels: List[float],
    avg_levels: List[float],
    lead_times: List[int],
    params: Dict[str, Any],
    moving_average_window: int = 30,
    max_scenarios: int = 100,
    figsize: Tuple[int, int] = (15, 15),
    output_dir: str = "src/pyps_invsim/outputs"
) -> plt.Figure:
    """
    Create a comprehensive dashboard of simulation results according to the visualization requirements.
    
    Args:
        all_scenarios: List of inventory level lists for each scenario
        all_demands: List of demand lists for each scenario
        min_levels: List of minimum inventory levels for each scenario
        avg_levels: List of average inventory levels for each scenario
        lead_times: List of lead time values
        params: Simulation parameters
        moving_average_window: Window size for moving average calculation
        max_scenarios: Maximum number of scenarios to plot
        figsize: Figure size as (width, height)
        output_dir: Directory to save the figure
        
    Returns:
        Matplotlib figure
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Create figure with custom grid layout for 3 rows
    fig = plt.figure(figsize=figsize)
    gs = gridspec.GridSpec(3, 5, height_ratios=[2, 2, 1])
    
    # Chart 1: Inventory Performance across all scenarios (Row 1, columns 1-5)
    ax1 = fig.add_subplot(gs[0, :])
    
    # Plot inventory levels for each scenario
    for i, scenario in enumerate(all_scenarios[:max_scenarios]):
        ax1.plot(scenario, alpha=0.7)
    
    ax1.set_title('Inventory History for each Scenario')
    ax1.set_xlabel('Day of simulation')
    ax1.set_ylabel('Quantity')
    
    # Make axes cross at zero
    ax1.spines['left'].set_position('zero')
    ax1.spines['bottom'].set_position('zero')
    ax1.spines['right'].set_visible(False)
    ax1.spines['top'].set_visible(False)
    
    # Chart 2: Demand across all scenarios (Row 2, columns 1-5)
    ax2 = fig.add_subplot(gs[1, :])
    
    # Calculate and plot 30-day moving average demand * 30 (monthly demand) for each scenario
    if all_demands:
        for i, demands in enumerate(all_demands[:max_scenarios]):
            # Calculate moving average
            moving_avg = []
            for j in range(len(demands)):
                if j < moving_average_window:
                    # For early periods, use available data
                    window_avg = sum(demands[:j+1]) / (j+1) if j+1 > 0 else 0
                else:
                    # For later periods, use moving_average_window
                    window_avg = sum(demands[j-moving_average_window+1:j+1]) / moving_average_window
                moving_avg.append(window_avg * 30)  # Convert to monthly demand
            
            # Plot the moving average as light grey line
            ax2.plot(moving_avg, '-', color='lightgrey', linewidth=1, alpha=0.7)
    
    ax2.set_title('Moving Average Monthly Demand For Each Scenario')
    ax2.set_xlabel('Day of simulation')
    ax2.set_ylabel('Quantity (Monthly Demand)')
    
    # Make axes cross at zero
    ax2.spines['left'].set_position('zero')
    ax2.spines['bottom'].set_position('zero')
    ax2.spines['right'].set_visible(False)
    ax2.spines['top'].set_visible(False)
    
    # Chart 3: Histogram - stockout days per scenario (Row 3, column 1)
    ax3 = fig.add_subplot(gs[2, 0])
    
    # Calculate stockout days for each scenario
    stockout_days_per_scenario = []
    
    if all_scenarios:
        for scenario in all_scenarios:
            # Count days where inventory is zero
            scenario_stockout_days = sum(1 for inv in scenario if inv <= 0)
            stockout_days_per_scenario.append(scenario_stockout_days)
    
    # Create histogram
    ax3.hist(stockout_days_per_scenario, bins=30)
    ax3.set_title('Stockout Days per Scenario')
    ax3.set_xlabel('Number of stockout days')
    ax3.set_ylabel('Count of scenarios')
    
    # Add mean line
    mean_stockouts = np.mean(stockout_days_per_scenario) if stockout_days_per_scenario else 0
    ax3.axvline(mean_stockouts, color='red', linestyle=':',
                label=f'Mean ({mean_stockouts:.2f})')
    
    # Add 95th percentile line
    if stockout_days_per_scenario:
        percentile_95 = np.percentile(stockout_days_per_scenario, 95)
        ax3.axvline(percentile_95, color='green', linestyle=':',
                    label=f'95th percentile ({percentile_95:.2f})')
    
    ax3.legend(loc='best', fontsize='small')
    
    # Chart 4: Histogram - average inventory days (Row 3, column 2)
    ax4 = fig.add_subplot(gs[2, 1])
    
    # Calculate inventory days for each scenario using the utility function
    from pyps_invsim.utils.inventory_utils import calculate_inventory_days_for_scenarios
    
    inventory_days_per_scenario = calculate_inventory_days_for_scenarios(
        all_scenarios=all_scenarios,
        all_demands=all_demands,
        moving_average_window=moving_average_window
    )
    
    # Create histogram
    ax4.hist(inventory_days_per_scenario, bins=30)
    ax4.set_title('Average Inventory Days per Scenario')
    ax4.set_xlabel('Days of inventory')
    ax4.set_ylabel('Count of scenarios')
    
    # Add 5th and 95th percentile lines
    if inventory_days_per_scenario:
        percentile_5 = np.percentile(inventory_days_per_scenario, 5)
        percentile_95 = np.percentile(inventory_days_per_scenario, 95)
        ax4.axvline(percentile_5, color='red', linestyle=':',
                    label=f'5th percentile ({percentile_5:.2f})')
        ax4.axvline(percentile_95, color='red', linestyle=':',
                    label=f'95th percentile ({percentile_95:.2f})')
    ax4.legend(loc='best', fontsize='small')
    
    # Chart 5: Histogram - daily demand (Row 3, column 3)
    ax5 = fig.add_subplot(gs[2, 2])
    # Flatten all demands into a single list
    flat_demands = [demand for scenario_demands in all_demands for demand in scenario_demands]
    ax5.hist(flat_demands, bins=30)
    ax5.set_title('Daily Demand')
    ax5.set_xlabel('Daily demand quantity')
    ax5.set_ylabel('Count of days')
    
    # Add mean line
    mean_demand = np.mean(flat_demands)
    ax5.axvline(mean_demand, color='green', linestyle=':', 
                label=f'Mean ({mean_demand:.2f})')
    ax5.legend(loc='best', fontsize='small')
    
    # Chart 6: Histogram - supply lead-time (Row 3, column 4)
    ax6 = fig.add_subplot(gs[2, 3])
    
    # Check if lead_times is not empty
    if lead_times:
        ax6.hist(lead_times, bins=range(min(lead_times), max(lead_times) + 2, 1))
        # Add mean line
        mean_lead_time = np.mean(lead_times)
        ax6.axvline(mean_lead_time, color='green', linestyle=':',
                    label=f'Mean ({mean_lead_time:.2f})')
        # Add legend only if we have lead times
        if lead_times:
            ax6.legend(loc='best', fontsize='small')
    else:
        ax6.text(0.5, 0.5, 'No lead time data available',
                 horizontalalignment='center', verticalalignment='center',
                 transform=ax6.transAxes)
    
    ax6.set_title('Supply Lead-Time')
    ax6.set_xlabel('Lead-time in days')
    ax6.set_ylabel('Count of orders')
    # Legend is already added above if lead_times is not empty
    
    # Chart 7: Table - Parameters and Metrics (Row 3, column 5)
    ax7 = fig.add_subplot(gs[2, 4])
    ax7.axis('tight')
    ax7.axis('off')
    
    # Calculate service level and stockouts
    service_level = 0
    stockouts = 0
    stockout_days_per_scenario = []
    
    if all_scenarios and all_demands:
        total_demand_days = 0
        total_service_days = 0
        
        for scenario_idx in range(len(all_scenarios)):
            inventory = all_scenarios[scenario_idx]
            demands = all_demands[scenario_idx] if scenario_idx < len(all_demands) else []
            
            scenario_demand_days = 0
            scenario_service_days = 0
            scenario_stockout_days = 0
            
            for day_idx in range(min(len(inventory), len(demands))):
                # Count days with demand for service level calculation
                if demands[day_idx] > 0:
                    scenario_demand_days += 1
                    if inventory[day_idx] > 0:
                        scenario_service_days += 1
                
                # Count all days with zero inventory as stockout days
                # regardless of whether there was demand
                if inventory[day_idx] <= 0:
                    scenario_stockout_days += 1
            
            # Add to totals
            total_demand_days += scenario_demand_days
            total_service_days += scenario_service_days
            stockout_days_per_scenario.append(scenario_stockout_days)
        
        # Calculate service level as percentage
        service_level = (total_service_days / total_demand_days * 100) if total_demand_days > 0 else 0
        
        # Calculate average stockouts per scenario
        stockouts = np.mean(stockout_days_per_scenario) if stockout_days_per_scenario else 0
    
    # Prepare table data
    table_data = [
        ['Parameter', 'Value'],
        ['reorder_method', params.get('reorder_method', 'N/A')],
        ['trend_monthly_rate', params.get('trend_monthly_rate', 'N/A')],
        ['min_days', params.get('min_days', 'N/A')],
        ['max_days', params.get('max_days', 'N/A')],
        ['reorder_point', params.get('reorder_point', 'N/A')],
        ['max_quantity', params.get('max_quantity', 'N/A')],
        ['seasonality_weight', params.get('seasonality_weight', 'N/A')],
        ['trend_weight', params.get('trend_weight', 'N/A')],
        ['noise_weight', params.get('demand_dispersion_parameter', 'N/A')],
        ['service level %', f'{service_level:.2f}%'],
        ['avg stockout days', f'{stockouts:.2f}']
    ]
    
    # Create table
    table = ax7.table(cellText=table_data, loc='center', cellLoc='left')
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.5)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save the figure
    output_path = os.path.join(output_dir, 'inventory_dashboard.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    
    return fig

def save_dashboard(
    all_scenarios: List[List[float]],
    all_demands: List[List[float]],
    min_levels: List[float],
    avg_levels: List[float],
    lead_times: List[int],
    params: Dict[str, Any],
    output_dir: str = "src/pyps_invsim/outputs",
    filename: str = "inventory_dashboard.png"
) -> str:
    """
    Create and save the inventory dashboard.
    
    Args:
        all_scenarios: List of inventory level lists for each scenario
        all_demands: List of demand lists for each scenario
        min_levels: List of minimum inventory levels for each scenario
        avg_levels: List of average inventory levels for each scenario
        lead_times: List of lead time values
        params: Simulation parameters
        output_dir: Directory to save the figure
        filename: Filename for the saved figure
        
    Returns:
        Path to the saved figure
    """
    # Get moving_average_window from params
    moving_average_window = params.get('moving_average_window', 30)
    
    # Create the dashboard
    fig = create_inventory_dashboard(
        all_scenarios=all_scenarios,
        all_demands=all_demands,
        min_levels=min_levels,
        avg_levels=avg_levels,
        lead_times=lead_times,
        params=params,
        moving_average_window=moving_average_window,
        output_dir=output_dir
    )
    
    # Save the figure
    output_path = os.path.join(output_dir, filename)
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    
    return output_path