# Path Utilities for PyPS_InvSim

This document explains how the path utilities in PyPS_InvSim work and how to use them effectively.

## Overview

The path utilities provide a robust way to locate files and directories in both development and installed package environments. They handle cross-platform path resolution and provide fallback mechanisms when primary paths aren't available.

## Key Functions

### `find_project_root()`

Finds the project root directory in both development and installed package environments.

- In development, it looks for markers like `pyproject.toml` or `.git`
- For installed packages, it uses environment variables or default locations
- Works across different operating systems

### `get_data_dir()`

Gets the directory for data files.

- Checks multiple possible locations and uses the first valid one
- Works in both development and installed package environments

### `get_excel_dir()`

Gets the directory for Excel files.

- Checks multiple possible locations and uses the first valid one
- Works in both development and installed package environments

### `get_invsim_excel_file()`

Gets the path to the InvSim Excel file.

- First checks for an environment variable
- Then looks for Excel files with the InvSim_Parameters table
- Finally falls back to the default path

## Environment Variables

The path utilities support the following environment variables:

- `PYPS_INVSIM_ROOT`: Override the project root directory
- `PYPS_INVSIM_DATA`: Override the data directory
- `PYPS_INVSIM_EXCEL`: Override the Excel directory
- `PYPS_INVSIM_EXCEL_FILE`: Override the Excel file path

## Usage Examples

### Basic Usage

```python
from pyps_invsim.utils.path_utils import get_invsim_excel_file

# Get the path to the InvSim Excel file
excel_file = get_invsim_excel_file()
```

### With Environment Variables

```bash
# Set environment variables
export PYPS_INVSIM_EXCEL_FILE=/path/to/custom/excel/file.xlsm

# Run your script
python my_script.py
```

### Cross-Platform Support

The path utilities work on Windows, macOS, and Linux:

- Windows: Uses `%APPDATA%\pyps_invsim` for user data
- macOS/Linux: Uses `~/.pyps_invsim` for user data

## Testing

Two test files are provided to verify that the path utilities work correctly:

1. `tests/test_path_utils_robust.py`: Unit tests for different environments
2. `scripts/test_path_resolution.py`: Script to test path resolution in real environments

To run the tests:

```bash
# Run unit tests
pytest tests/test_path_utils_robust.py

# Run the path resolution script
python scripts/test_path_resolution.py
```

## Best Practices

1. Always use the path utilities instead of hardcoding paths
2. Use environment variables for configurable paths in production
3. Test your code in both development and installed package environments
4. Test on different operating systems if possible

## Troubleshooting

If you encounter path-related issues:

1. Run `scripts/test_path_resolution.py` to see how paths are resolved
2. Check if the required directories and files exist
3. Try setting environment variables to override paths
4. Ensure your package is installed correctly if running as an installed package