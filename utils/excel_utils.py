"""
Utility functions for working with Excel files.
"""
import openpyxl
import csv
import os
import pandas as pd
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from pathlib import Path
import uuid

# Module-level cache for Excel parameters
# Structure: {(filepath, table_name): parameters_dict}
_parameter_cache: Dict[tuple, Dict[str, Any]] = {}

def load_excel_parameters(
    filepath: str,
    table_name: Optional[str] = None,
    required_vars: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Load parameters from an Excel file.
    
    Args:
        filepath (str): Path to the Excel file
        table_name (str, optional): Name of the table to search for first
        required_vars (list, optional): List of variable names to find
            If None, returns all variables found
        
    Returns:
        dict: Dictionary containing all found parameters
    
    Raises:
        ValueError: If required variables are not found
    """
    # Create cache key from filepath and table_name
    cache_key = (filepath, table_name)
    
    # Check if parameters are already cached
    if cache_key in _parameter_cache:
        params = _parameter_cache[cache_key]
        # If required_vars is specified, verify all are in the cached params
        if required_vars and not all(var in params for var in required_vars):
            # If not all required vars are in cache, we need to reload
            pass
        else:
            return params
    
    # Load the Excel workbook
    wb = openpyxl.load_workbook(filepath, data_only=True)
    found_params = {}
    
    # If table_name is specified, try different approaches to find it
    if table_name:
        # First, check if it's a named range that references a table
        if table_name in wb.defined_names:
            found_params = _find_in_named_table(wb, table_name)
        
        # If no parameters found, try looking for a cell containing the table name
        if not found_params:
            found_params = _find_table_by_name(wb, table_name)
        
        # Try to find the table as a sheet name (if no 'Table' suffix)
        if not found_params and not table_name.endswith("_Table"):
            sheet_name = table_name
            if sheet_name in wb.sheetnames:
                found_params = _extract_params_from_sheet(wb[sheet_name])
        
        # Try to find by related sheet name (if has 'Table' suffix)
        if not found_params and table_name.endswith("_Table"):
            sheet_name = table_name.rsplit("_Table", 1)[0]
            if sheet_name in wb.sheetnames:
                found_params = _extract_params_from_sheet(wb[sheet_name])
        
        # If we found the table and it has all required variables, return it
        if found_params and (not required_vars or all(var in found_params for var in required_vars)):
            _parameter_cache[cache_key] = found_params
            return found_params
    
    # If we get here, either no table_name was specified, or we didn't find the table,
    # or the table didn't have all required variables
    
    # Check named ranges
    named_range_params = _find_in_named_ranges(wb, required_vars)
    if named_range_params and (not required_vars or all(var in named_range_params for var in required_vars)):
        _parameter_cache[cache_key] = named_range_params
        return named_range_params
    
    # Search through all worksheets for tables
    table_params = _find_in_tables(wb, required_vars)
    if table_params and (not required_vars or all(var in table_params for var in required_vars)):
        _parameter_cache[cache_key] = table_params
        return table_params
    
    # If we get here and required_vars is specified, we couldn't find all required variables
    if required_vars and not all(var in found_params for var in required_vars):
        missing_vars = [var for var in required_vars if var not in found_params]
        raise ValueError(
            f"Could not find all required parameters in {filepath}. "
            f"Missing: {', '.join(missing_vars)}"
        )
    
    # If required_vars is not specified, return whatever we found
    _parameter_cache[cache_key] = found_params
    return found_params

def write_simulation_csv(
    data: List[Dict[str, Any]],
    output_dir: str,
    filename: str,
    headers: Optional[List[str]] = None,
    decimal_places: int = 2
) -> str:
    """
    Write simulation data to a CSV file.
    
    Args:
        data (List[Dict[str, Any]]): List of dictionaries containing data to write
        output_dir (str): Directory to write the CSV file to
        filename (str): Name of the CSV file
        headers (List[str], optional): List of column headers. If None, uses keys from first dict.
        decimal_places (int, optional): Number of decimal places for float values. Defaults to 2.
        
    Returns:
        str: Path to the created CSV file
    """
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Construct the full file path
    file_path = os.path.join(output_dir, filename)
    
    # If no data, write an empty file
    if not data:
        with open(file_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([])
        return file_path
    
    # If headers not provided, use keys from first dictionary
    if headers is None:
        headers = list(data[0].keys())
    
    # Format numeric values to specified decimal places
    formatted_data = []
    for row in data:
        formatted_row = {}
        for key, value in row.items():
            if isinstance(value, float):
                formatted_row[key] = round(value, decimal_places)
            else:
                formatted_row[key] = value
        formatted_data.append(formatted_row)
    
    # Write the data to the CSV file
    with open(file_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        writer.writerows(formatted_data)
    
    return file_path

def generate_simulation_id(prefix: str = "sim") -> str:
    """
    Generate a unique simulation ID in the format prefix_YYYYMMDDHHMMSS_uuid.
    
    Args:
        prefix (str, optional): Prefix for the simulation ID. Defaults to "sim".
        
    Returns:
        str: Simulation ID
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]  # Use first 8 chars of UUID
    return f"{prefix}_{timestamp}_{unique_id}"

def _extract_params_from_sheet(sheet):
    """Extract parameters from a sheet with a name-value layout."""
    params = {}
    
    # Look for a header row containing "VariableName" or similar
    header_row = None
    name_col = None
    value_col = None
    
    # Find the header row and columns
    for row in range(1, sheet.max_row + 1):
        for col in range(1, min(10, sheet.max_column + 1)):
            cell_value = sheet.cell(row=row, column=col).value
            if cell_value and isinstance(cell_value, str):
                if "variablename" in cell_value.lower():
                    header_row = row
                    name_col = col
                elif "variablevalue" in cell_value.lower() and header_row == row:
                    value_col = col
    
    # If we found a header row with name and value columns
    if header_row and name_col and value_col:
        # Extract parameters from rows below the header
        for row in range(header_row + 1, sheet.max_row + 1):
            name = sheet.cell(row=row, column=name_col).value
            value = sheet.cell(row=row, column=value_col).value
            if name and isinstance(name, str) and name.strip():
                params[name.strip()] = value
    
    return params

def _find_in_named_table(wb, table_name):
    """Find parameters in a named table."""
    params = {}
    
    if table_name in wb.defined_names:
        # Get all the destinations for this named range
        for sheet_name, coord in wb.defined_names[table_name].destinations:
            sheet = wb[sheet_name]
            
            # Try to interpret this as a table reference
            # It could be a single cell or a range
            if ":" in coord:  # It's a range (e.g., "A1:B10")
                start_cell, end_cell = coord.split(":")
                # Extract the table data from this range
                # Assuming first row is headers
                start_coord = openpyxl.utils.cell.coordinate_from_string(start_cell)
                end_coord = openpyxl.utils.cell.coordinate_from_string(end_cell)
                
                start_col = openpyxl.utils.column_index_from_string(start_coord[0])
                start_row = start_coord[1]
                end_col = openpyxl.utils.column_index_from_string(end_coord[0])
                end_row = end_coord[1]
                
                # Check for horizontal table (with column headers)
                header_row = start_row
                name_col = None
                value_col = None
                
                # Look for "VariableName" and "VariableValue" in the first row
                for col in range(start_col, end_col + 1):
                    cell_value = sheet.cell(row=header_row, column=col).value
                    if cell_value and isinstance(cell_value, str):
                        if "variablename" in cell_value.lower():
                            name_col = col
                        elif "variablevalue" in cell_value.lower():
                            value_col = col
                
                # If found column headers, extract parameters
                if name_col and value_col:
                    for row in range(header_row + 1, end_row + 1):
                        name = sheet.cell(row=row, column=name_col).value
                        value = sheet.cell(row=row, column=value_col).value
                        if name and isinstance(name, str) and name.strip():
                            params[name.strip()] = value
            else:
                # It's a single cell
                cell = sheet[coord]
                
                # This might be the top-left cell of a table
                row = cell.row
                col = cell.column
                
                # Try to find headers in this row or next row
                header_cells = []
                for c in range(col, min(col + 10, sheet.max_column + 1)):
                    header_cells.append(sheet.cell(row=row, column=c).value)
                
                # If no headers in current row, try next row
                if not any(header_cells):
                    row += 1
                    header_cells = []
                    for c in range(col, min(col + 10, sheet.max_column + 1)):
                        header_cells.append(sheet.cell(row=row, column=c).value)
                
                # Look for "VariableName" and "VariableValue" in headers
                name_col = None
                value_col = None
                for i, cell_value in enumerate(header_cells):
                    if cell_value and isinstance(cell_value, str):
                        if "variablename" in cell_value.lower():
                            name_col = col + i
                        elif "variablevalue" in cell_value.lower():
                            value_col = col + i
                
                # If found column headers, extract parameters
                if name_col and value_col:
                    for r in range(row + 1, min(row + 30, sheet.max_row + 1)):
                        name = sheet.cell(row=r, column=name_col).value
                        value = sheet.cell(row=r, column=value_col).value
                        if name and isinstance(name, str) and name.strip():
                            params[name.strip()] = value
                        elif not name:  # Stop at first empty name
                            break
    
    return params

def _find_table_by_name(wb, table_name: str) -> Dict[str, Any]:
    """Find a table with the specified name in the workbook."""
    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        
        # Look for a cell containing the table name
        for row in range(1, sheet.max_row + 1):
            for col in range(1, sheet.max_column + 1):
                cell_value = sheet.cell(row=row, column=col).value
                
                if cell_value and isinstance(cell_value, str) and cell_value.lower() == table_name.lower():
                    # Found the table name, now extract the parameters
                    # Assume the table has headers in the next row and values in the row after that
                    if row + 2 <= sheet.max_row:
                        # Check for horizontal table (headers in columns)
                        header_row = row + 1
                        value_row = row + 2
                        params = {}
                        
                        for c in range(1, sheet.max_column + 1):
                            header = sheet.cell(row=header_row, column=c).value
                            if header and isinstance(header, str):
                                value = sheet.cell(row=value_row, column=c).value
                                params[header] = value
                        
                        if params:
                            return params
                    
                    # Check for vertical table (headers in first column, values in second)
                    params = {}
                    for r in range(row + 1, min(row + 21, sheet.max_row)):  # Check next 20 rows at most
                        name_cell = sheet.cell(row=r, column=col).value
                        if name_cell and isinstance(name_cell, str):
                            value_cell = sheet.cell(row=r, column=col + 1).value
                            params[name_cell] = value_cell
                    
                    if params:
                        return params
    
    return {}

def _find_in_named_ranges(wb, required_vars: Optional[List[str]] = None) -> Dict[str, Any]:
    """Find parameters in named ranges."""
    found_params = {}
    
    # Check if the workbook has defined names
    if wb.defined_names:
        for name in wb.defined_names:
            # Skip hidden names
            if name.startswith('_'):
                continue
            
            # If required_vars is specified, only look for those
            if required_vars and name.lower() not in [var.lower() for var in required_vars]:
                continue
            
            # Get the destinations for this name
            dests = wb.defined_names[name].destinations
            
            for sheet_name, coord in dests:
                sheet = wb[sheet_name]
                cell = sheet[coord]
                found_params[name] = cell.value
    
    return found_params

def _find_in_tables(wb, required_vars: Optional[List[str]] = None) -> Dict[str, Any]:
    """Find parameters in tables throughout the workbook."""
    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        
        # Look for tables in the sheet
        for row in range(1, sheet.max_row + 1):
            var_names = []
            var_values = []
            
            # Check if this row could be a header row
            for col in range(1, sheet.max_column + 1):
                cell_value = sheet.cell(row=row, column=col).value
                if cell_value and isinstance(cell_value, str):
                    var_names.append(cell_value)
                    
                    # Get the value from the cell below
                    if row < sheet.max_row:
                        var_values.append(sheet.cell(row=row+1, column=col).value)
            
            # Check if all required variables are in this row
            if required_vars and all(var.lower() in [name.lower() for name in var_names] for var in required_vars):
                # Create a dictionary mapping variable names to values
                params = {}
                for i, name in enumerate(var_names):
                    if i < len(var_values):
                        params[name] = var_values[i]
                return params
            elif not required_vars and var_names and var_values:
                # If no required_vars specified, return all variables found
                params = {}
                for i, name in enumerate(var_names):
                    if i < len(var_values):
                        params[name] = var_values[i]
                return params
            
            # Also check if this row could be a variable name column
            if len(var_names) == 1 and row < sheet.max_row:
                # Start collecting variables from this point
                potential_params = {}
                for r in range(row, min(row + 20, sheet.max_row)):  # Check next 20 rows at most
                    name_cell = sheet.cell(row=r, column=1).value
                    value_cell = sheet.cell(row=r, column=2).value
                    
                    if name_cell and isinstance(name_cell, str):
                        potential_params[name_cell] = value_cell
                
                # Check if we found all required variables
                if required_vars and all(var.lower() in [name.lower() for name in potential_params.keys()] for var in required_vars):
                    return potential_params
                elif not required_vars and potential_params:
                    return potential_params
    
    return {}

# Add the missing functions for the tests

def insert_dashboard_image_to_excel(
    excel_file: str,
    image_path: str,
    table_name: str = "InvSim_Parameters",
    dashboard_sheet_name: str = "InvSim_Dashboard"
) -> bool:
    """
    Import function from excel_dashboard module to avoid circular imports.
    
    This is a wrapper function that calls the actual implementation in excel_dashboard.py.
    """
    from pyps_invsim.utils.excel_dashboard import insert_dashboard_image_to_excel as impl
    return impl(excel_file, image_path, table_name, dashboard_sheet_name)

def write_excel_report(
    data: Dict[str, pd.DataFrame],
    output_path: str,
    index: bool = True
) -> str:
    """
    Write multiple DataFrames to an Excel file, one per sheet.
    
    Args:
        data (Dict[str, pd.DataFrame]): Dictionary mapping sheet names to DataFrames
        output_path (str): Path to the output Excel file
        index (bool, optional): Whether to include the DataFrame index. Defaults to True.
        
    Returns:
        str: Path to the created Excel file
    """
    # Create the output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Write the DataFrames to the Excel file
    with pd.ExcelWriter(output_path) as writer:
        for sheet_name, df in data.items():
            df.to_excel(writer, sheet_name=sheet_name, index=index)
    
    return output_path

def read_simulation_csv(
    filepath: str,
    convert_types: bool = True
) -> List[Dict[str, Any]]:
    """
    Read simulation data from a CSV file.
    
    Args:
        filepath (str): Path to the CSV file
        convert_types (bool, optional): Whether to convert string values to appropriate types. Defaults to True.
        
    Returns:
        List[Dict[str, Any]]: List of dictionaries containing the CSV data
    """
    data = []
    
    with open(filepath, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            if convert_types:
                # Convert string values to appropriate types
                converted_row = {}
                for key, value in row.items():
                    if value == '':
                        converted_row[key] = None
                    elif value.lower() == 'true':
                        converted_row[key] = True
                    elif value.lower() == 'false':
                        converted_row[key] = False
                    else:
                        try:
                            # Try to convert to int or float
                            if '.' in value:
                                converted_row[key] = float(value)
                            else:
                                converted_row[key] = int(value)
                        except ValueError:
                            # If conversion fails, keep as string
                            converted_row[key] = value
                data.append(converted_row)
            else:
                data.append(row)
    
    return data

def convert_to_dataframe(
    data: List[Dict[str, Any]]
) -> pd.DataFrame:
    """
    Convert a list of dictionaries to a pandas DataFrame.
    
    Args:
        data (List[Dict[str, Any]]): List of dictionaries
        
    Returns:
        pd.DataFrame: DataFrame containing the data
    """
    return pd.DataFrame(data)

def filter_dataframe(
    df: pd.DataFrame,
    filters: Dict[str, Any]
) -> pd.DataFrame:
    """
    Filter a DataFrame based on column values.
    
    Args:
        df (pd.DataFrame): DataFrame to filter
        filters (Dict[str, Any]): Dictionary mapping column names to filter values
        
    Returns:
        pd.DataFrame: Filtered DataFrame
    """
    filtered_df = df.copy()
    
    for column, value in filters.items():
        if column in filtered_df.columns:
            filtered_df = filtered_df[filtered_df[column] == value]
    
    return filtered_df

def aggregate_dataframe(
    df: pd.DataFrame,
    group_by: List[str],
    aggregations: Dict[str, str]
) -> pd.DataFrame:
    """
    Aggregate a DataFrame by grouping and applying aggregation functions.
    
    Args:
        df (pd.DataFrame): DataFrame to aggregate
        group_by (List[str]): List of columns to group by
        aggregations (Dict[str, str]): Dictionary mapping column names to aggregation functions
        
    Returns:
        pd.DataFrame: Aggregated DataFrame
    """
    # Group by the specified columns
    grouped = df.groupby(group_by)
    
    # Apply the aggregation functions
    aggregated = grouped.agg(aggregations)
    
    # Reset the index to make the grouped columns regular columns
    return aggregated.reset_index()
