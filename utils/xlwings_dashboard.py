"""
Excel dashboard utilities using xlwings for inventory simulations.
"""
import os
from pathlib import Path
from typing import Optional, Union
import xlwings as xw
import matplotlib.pyplot as plt

def insert_plot_to_excel_with_xlwings(
    excel_file: Union[str, Path],
    fig: plt.Figure = None,
    image_path: Optional[Union[str, Path]] = None,
    sheet_name: str = "InvSim_Parameters",
    title: str = "Inventory Simulation Dashboard",
    position: tuple = (0, 0),
    size: tuple = (800, 600)
) -> bool:
    """
    Insert a matplotlib figure or image into an Excel file using xlwings.
    
    Args:
        excel_file: Path to the Excel file
        fig: Matplotlib figure to insert (if provided, takes precedence over image_path)
        image_path: Path to the image file to insert (used if fig is None)
        sheet_name: Name of the sheet to insert the plot into
        title: Title to display above the plot
        position: Position (row, column) to insert the plot
        size: Size (width, height) of the plot in pixels
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Convert paths to Path objects
        if isinstance(excel_file, str):
            excel_file = Path(excel_file)
        
        if image_path and isinstance(image_path, str):
            image_path = Path(image_path)
        
        # Check if Excel file exists
        if not excel_file.exists():
            print(f"Excel file not found: {excel_file}")
            return False
        
        # Check if image exists (if we're using an image)
        if fig is None and image_path and not image_path.exists():
            print(f"Image file not found: {image_path}")
            return False
        
        # Open the Excel file with xlwings
        try:
            # Try to connect to an already open workbook first
            wb = xw.books[excel_file.name]
            print(f"Connected to already open workbook: {excel_file.name}")
        except:
            # If not open, open it
            wb = xw.Book(str(excel_file))
            print(f"Opened workbook: {excel_file}")
        
        # Check if the sheet exists, create it if not
        try:
            sheet = wb.sheets[sheet_name]
            print(f"Using existing sheet: {sheet_name}")
        except:
            sheet = wb.sheets.add(sheet_name)
            print(f"Created new sheet: {sheet_name}")
        
        # Clear the sheet
        sheet.clear()
        
        # Add a title
        sheet.range("A1").value = title
        sheet.range("A1").font.size = 16
        sheet.range("A1").font.bold = True
        
        # Insert the figure or image
        if fig is not None:
            # Insert the matplotlib figure directly
            sheet.pictures.add(
                fig,
                name="InvSimDashboard",
                update=True,
                left=sheet.range(f"A3").left,
                top=sheet.range(f"A3").top,
                width=size[0],
                height=size[1]
            )
            print("Inserted matplotlib figure into Excel")
        elif image_path:
            # Insert the image from file
            sheet.pictures.add(
                str(image_path),
                name="InvSimDashboard",
                update=True,
                left=sheet.range(f"A3").left,
                top=sheet.range(f"A3").top,
                width=size[0],
                height=size[1]
            )
            print(f"Inserted image from {image_path} into Excel")
        
        # Save the workbook
        wb.save()
        print(f"Saved workbook: {excel_file}")
        
        return True
    
    except Exception as e:
        print(f"Error inserting plot into Excel with xlwings: {e}")
        return False

def create_and_insert_dashboard(
    excel_file: Union[str, Path],
    all_scenarios,
    all_demands,
    min_levels,
    avg_levels,
    lead_times,
    params,
    sheet_name: str = "InvSim_Dashboard",
    max_scenarios_to_plot: int = 10
) -> bool:
    """
    Create a dashboard plot and insert it directly into Excel using xlwings.
    
    Args:
        excel_file: Path to the Excel file
        all_scenarios: List of inventory scenarios
        all_demands: List of demand histories
        min_levels: List of minimum inventory levels
        avg_levels: List of average inventory levels
        lead_times: List of lead times
        params: Simulation parameters
        sheet_name: Name of the sheet to insert the dashboard into
        max_scenarios_to_plot: Maximum number of scenarios to include in plots
        
    Returns:
        True if successful, False otherwise
    """
    try:
        import numpy as np
        
        # Create the dashboard figure with the same size as the PNG
        fig = plt.figure(figsize=(15, 12), dpi=100)
        
        # Random walk plot (top subplot)
        ax1 = fig.add_subplot(2, 1, 1)
        for scenario in all_scenarios[:max_scenarios_to_plot]:  # Plot limited number of scenarios for clarity
            ax1.plot(scenario)
        ax1.set_title('Inventory Level Random Walk', fontsize=14)
        ax1.set_xlabel('Period', fontsize=12)
        ax1.set_ylabel('Inventory Level', fontsize=12)
        ax1.grid(True, linestyle='--', alpha=0.7)
        
        # Function to add percentile lines to histogram
        def add_percentile_lines(ax, data):
            percentile_5 = np.percentile(data, 5)
            percentile_95 = np.percentile(data, 95)
            ax.axvline(percentile_5, color='red', linestyle=':', label='5th percentile')
            ax.axvline(percentile_95, color='red', linestyle=':', label='95th percentile')
            ax.legend(fontsize=8)
        
        # Minimum inventory level histogram
        ax2 = fig.add_subplot(2, 4, 5)
        ax2.hist(min_levels, bins=30, color='blue', alpha=0.7)
        ax2.set_title('Minimum Inventory Level', fontsize=12)
        add_percentile_lines(ax2, min_levels)
        ax2.grid(True, linestyle='--', alpha=0.5)
        
        # Average inventory level histogram
        ax3 = fig.add_subplot(2, 4, 6)
        ax3.hist(avg_levels, bins=30, color='blue', alpha=0.7)
        ax3.set_title('Average Inventory Level', fontsize=12)
        add_percentile_lines(ax3, avg_levels)
        ax3.grid(True, linestyle='--', alpha=0.5)
        
        # Daily demand histogram
        ax4 = fig.add_subplot(2, 4, 7)
        # Flatten all demands into a single list
        all_demands_flat = np.concatenate(all_demands).ravel()
        ax4.hist(all_demands_flat, bins=30, color='blue', alpha=0.7)
        ax4.set_title('Daily Demand', fontsize=12)
        add_percentile_lines(ax4, all_demands_flat)
        ax4.grid(True, linestyle='--', alpha=0.5)
        
        # Lead time histogram
        ax5 = fig.add_subplot(2, 4, 8)
        ax5.hist(lead_times, bins=range(int(min(lead_times)), int(max(lead_times)) + 2, 1),
                color='blue', alpha=0.7)
        ax5.set_title('Lead Time Distribution', fontsize=12)
        add_percentile_lines(ax5, lead_times)
        ax5.grid(True, linestyle='--', alpha=0.5)
        
        # Create a proper parameter table at the bottom
        # First, select key parameters to display
        key_params = {
            'demand_mean': params.get('demand_mean', 'N/A'),
            'demand_dispersion_parameter': params.get('demand_dispersion_parameter', 'N/A'),
            'reorder_point': params.get('reorder_point', 'N/A'),
            'reorder_quantity': params.get('reorder_quantity', 'N/A'),
            'supply_lt_mean': params.get('supply_lt_mean', 'N/A'),
            'num_scenarios': params.get('num_scenarios', 'N/A')
        }
        
        # Create a table-like text display
        param_text = "Parameters:\n"
        param_text += "\n".join([f"{k.replace('_', ' ')}: {v}" for k, v in key_params.items()])
        
        # Add a text box with parameters that looks like a table
        props = dict(boxstyle='round', facecolor='white', alpha=0.9)
        fig.text(0.01, 0.01, param_text, fontsize=10,
                verticalalignment='bottom',
                bbox=props)
        
        # Adjust layout with more space at the bottom for parameters
        plt.tight_layout(rect=[0, 0.05, 1, 0.98])
        
        # Insert the figure into Excel
        success = insert_plot_to_excel_with_xlwings(
            excel_file=excel_file,
            fig=fig,
            sheet_name=sheet_name,
            title="Inventory Simulation Dashboard",
            size=(900, 700)  # Slightly larger to ensure readability
        )
        
        # Close the figure to free memory
        plt.close(fig)
        
        return success
    
    except Exception as e:
        print(f"Error creating and inserting dashboard: {e}")
        return False