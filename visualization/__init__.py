"""
Visualization package for inventory simulations.
"""
from pyps_invsim.visualization.plotting import (
    plot_inventory_levels,
    plot_histogram,
    create_simulation_dashboard,
    add_percentile_lines,
    plot_order_quantities,
    plot_forecast_vs_orders,
    save_plots
)

from pyps_invsim.visualization.dashboard import (
    create_inventory_dashboard,
    save_dashboard
)

__all__ = [
    'plot_inventory_levels',
    'plot_histogram',
    'create_simulation_dashboard',
    'add_percentile_lines',
    'plot_order_quantities',
    'plot_forecast_vs_orders',
    'save_plots',
    'create_inventory_dashboard',
    'save_dashboard'
]