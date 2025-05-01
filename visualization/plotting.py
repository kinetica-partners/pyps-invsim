"""
Plotting functions for inventory simulations.
"""
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Any, Optional, Tuple, Union

def plot_inventory_levels(
    all_scenarios: List[List[float]],
    title: str = "Inventory Level Random Walk",
    max_scenarios: int = 100,
    figsize: Tuple[int, int] = (10, 6)
) -> plt.Figure:
    """
    Plot inventory levels for multiple scenarios.
    
    Args:
        all_scenarios: List of inventory level lists for each scenario
        title: Plot title
        max_scenarios: Maximum number of scenarios to plot
        figsize: Figure size as (width, height)
        
    Returns:
        Matplotlib figure
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    # Plot only up to max_scenarios for clarity
    for scenario in all_scenarios[:max_scenarios]:
        ax.plot(scenario)
    
    ax.set_title(title)
    ax.set_xlabel('Period')
    ax.set_ylabel('Inventory Level')
    
    return fig

def plot_histogram(
    data: List[float],
    title: str,
    xlabel: str,
    ylabel: str = "Frequency",
    bins: Union[int, List[float]] = 30,
    figsize: Tuple[int, int] = (8, 6),
    show_percentiles: bool = True,
    percentiles: List[int] = [5, 95]
) -> plt.Figure:
    """
    Plot a histogram of data with optional percentile lines.
    
    Args:
        data: Data to plot
        title: Plot title
        xlabel: X-axis label
        ylabel: Y-axis label
        bins: Number of bins or bin edges
        figsize: Figure size as (width, height)
        show_percentiles: Whether to show percentile lines
        percentiles: List of percentiles to show
        
    Returns:
        Matplotlib figure
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    ax.hist(data, bins=bins)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    
    if show_percentiles:
        for p in percentiles:
            percentile_value = np.percentile(data, p)
            ax.axvline(
                percentile_value, 
                color='red', 
                linestyle=':', 
                label=f'{p}th percentile ({percentile_value:.2f})'
            )
        ax.legend()
    
    return fig

def create_simulation_dashboard(
    all_scenarios: List[List[float]],
    all_demands: List[List[float]],
    min_levels: List[float],
    avg_levels: List[float],
    lead_times: List[int],
    figsize: Tuple[int, int] = (15, 12)
) -> plt.Figure:
    """
    Create a comprehensive dashboard of simulation results.
    
    Args:
        all_scenarios: List of inventory level lists for each scenario
        all_demands: List of demand lists for each scenario
        min_levels: List of minimum inventory levels for each scenario
        avg_levels: List of average inventory levels for each scenario
        lead_times: List of lead time values
        figsize: Figure size as (width, height)
        
    Returns:
        Matplotlib figure
    """
    fig = plt.figure(figsize=figsize)
    
    # Random walk plot
    ax1 = fig.add_subplot(2, 1, 1)
    for scenario in all_scenarios[:100]:  # Plot first 100 scenarios for clarity
        ax1.plot(scenario)
    ax1.set_title('Inventory Level Random Walk')
    ax1.set_xlabel('Period')
    ax1.set_ylabel('Inventory Level')
    
    # Minimum inventory histogram
    ax2 = fig.add_subplot(2, 4, 5)
    ax2.hist(min_levels, bins=30)
    ax2.set_title('Minimum Inventory Level')
    add_percentile_lines(ax2, min_levels)
    
    # Average inventory histogram
    ax3 = fig.add_subplot(2, 4, 6)
    ax3.hist(avg_levels, bins=30)
    ax3.set_title('Average Inventory Level')
    add_percentile_lines(ax3, avg_levels)
    
    # Daily demand histogram
    ax4 = fig.add_subplot(2, 4, 7)
    # Flatten all demands into a single list
    flat_demands = [demand for scenario_demands in all_demands for demand in scenario_demands]
    ax4.hist(flat_demands, bins=30)
    ax4.set_title('Daily Demand')
    add_percentile_lines(ax4, flat_demands)
    
    # Lead time histogram
    ax5 = fig.add_subplot(2, 4, 8)
    ax5.hist(lead_times, bins=range(min(lead_times), max(lead_times) + 2, 1))
    ax5.set_title('Lead Time Distribution')
    add_percentile_lines(ax5, lead_times)
    
    plt.tight_layout()
    return fig

def add_percentile_lines(ax, data):
    """
    Add percentile lines to a histogram.
    
    Args:
        ax: Matplotlib axis
        data: Data used for the histogram
    """
    percentile_5 = np.percentile(data, 5)
    percentile_95 = np.percentile(data, 95)
    ax.axvline(percentile_5, color='red', linestyle=':', label=f'5th percentile ({percentile_5:.2f})')
    ax.axvline(percentile_95, color='red', linestyle=':', label=f'95th percentile ({percentile_95:.2f})')
    ax.legend()

def plot_order_quantities(
    order_history: List[Dict[str, Any]],
    figsize: Tuple[int, int] = (12, 8)
) -> plt.Figure:
    """
    Plot order quantities over time and as a distribution.
    
    Args:
        order_history: List of order event dictionaries
        figsize: Figure size as (width, height)
        
    Returns:
        Matplotlib figure
    """
    if not order_history:
        # Create an empty figure if no orders
        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(1, 1, 1)
        ax.text(0.5, 0.5, "No orders placed", ha='center', va='center')
        return fig
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
    
    # Extract days and quantities
    days = [order['day'] for order in order_history]
    quantities = [order['quantity'] for order in order_history]
    
    # Plot quantities over time
    ax1.plot(days, quantities, 'o-')
    ax1.set_title('Order Quantities by Day')
    ax1.set_xlabel('Day')
    ax1.set_ylabel('Order Quantity')
    
    # Plot quantity distribution
    ax2.hist(quantities, bins=20)
    ax2.set_title('Order Quantity Distribution')
    ax2.set_xlabel('Order Quantity')
    ax2.set_ylabel('Frequency')
    
    plt.tight_layout()
    return fig

def plot_forecast_vs_orders(
    order_history: List[Dict[str, Any]],
    figsize: Tuple[int, int] = (10, 6)
) -> Optional[plt.Figure]:
    """
    Plot forecast values against order quantities.
    
    Args:
        order_history: List of order event dictionaries
        figsize: Figure size as (width, height)
        
    Returns:
        Matplotlib figure or None if forecast data is not available
    """
    # Check if forecast data is available
    if not order_history or 'forecast' not in order_history[0]:
        return None
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # Extract forecasts and quantities
    forecasts = []
    quantities = []
    
    for order in order_history:
        forecast = order.get('forecast')
        if forecast is not None:
            # Handle both single value and list forecasts
            if isinstance(forecast, list):
                forecast = sum(forecast) / len(forecast)
            forecasts.append(forecast)
            quantities.append(order['quantity'])
    
    if not forecasts:
        ax.text(0.5, 0.5, "No forecast data available", ha='center', va='center')
        return fig
    
    # Plot scatter of forecast vs order quantity
    ax.scatter(forecasts, quantities)
    
    # Add a reference line (y=x)
    min_val = min(min(forecasts), min(quantities))
    max_val = max(max(forecasts), max(quantities))
    ax.plot([min_val, max_val], [min_val, max_val], 'r--', label='y=x')
    
    ax.set_title('Forecast vs Order Quantity')
    ax.set_xlabel('Forecast')
    ax.set_ylabel('Order Quantity')
    ax.legend()
    
    return fig

def save_plots(
    figures: Dict[str, plt.Figure],
    output_dir: str = "analysis",
    format: str = "png"
) -> Dict[str, str]:
    """
    Save multiple figures to files.
    
    Args:
        figures: Dictionary mapping figure names to Figure objects
        output_dir: Directory to save figures
        format: File format (e.g., 'png', 'jpg', 'pdf')
        
    Returns:
        Dictionary mapping figure names to file paths
    """
    import os
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    saved_paths = {}
    
    for name, fig in figures.items():
        # Create a valid filename
        filename = f"{name.lower().replace(' ', '_')}.{format}"
        filepath = os.path.join(output_dir, filename)
        
        # Save the figure
        fig.savefig(filepath)
        saved_paths[name] = filepath
    
    return saved_paths