# PyPS InvSim

A Python package for inventory simulation.

## Installation

### Option 1: Install from GitHub

You can install the package directly from GitHub:

```bash
pip install git+https://github.com/yourusername/pyps-invsim.git
```

### Option 2: Clone and Install Locally

Clone the repository and install locally:

```bash
# Using Git
git clone https://github.com/yourusername/pyps-invsim.git
cd pyps-invsim
pip install -e .
```

### Option 3: Download ZIP and Install

1. Download the ZIP file from GitHub
2. Extract the contents to a directory of your choice
3. Navigate to the extracted directory
4. Install the requirements:

```bash
# Using Bash
cd pyps-invsim
pip install -r requirements.txt

# Using PowerShell
cd pyps-invsim
pip install -r requirements.txt
```

## Dependencies

The package requires the following dependencies:

- matplotlib>=3.10.1
- numpy>=2.2.4
- openpyxl>=3.1.5
- pandas>=2.2.3
- pyyaml>=6.0.2
- scipy>=1.15.2

You can install all dependencies using the requirements.txt file:

```bash
# Using Bash
pip install -r requirements.txt

# Using PowerShell
pip install -r \requirements.txt
```

## Usage

### Basic Usage

```python
from pyps_invsim.simulations import run_inventory_simulation
from pyps_invsim.utils.config_utils import load_default_parameters

# Load default parameters
params = load_default_parameters('config/default_parameters.yaml')

# Run simulation
results = run_inventory_simulation(params)

# Analyze results
print(f"Average inventory level: {results[0]['final_inventory']}")
```

### Running from Command Line

You can run the simulation directly from the command line:

```bash
# Using Bash
python -m src.pyps_invsim.simulations.level1_inventory_simulation --num_scenarios 10

# Using PowerShell
python -m src.pyps_invsim.simulations.level1_inventory_simulation --num_scenarios 10
```

### Using Excel Parameters

The package can load parameters from an Excel file:

```bash
# Using Bash
python -m src.pyps_invsim.simulations.level1_inventory_simulation --excel_file "path/to/your/excel_file.xlsm" --table_name "InvSim_Parameters"

# Using PowerShell
python -m src.pyps_invsim.simulations.level1_inventory_simulation --excel_file "path\to\your\excel_file.xlsm" --table_name "InvSim_Parameters"
```

By default, the package looks for an Excel file named `PyPS_InvSim_v0.1.0.xlsm` in the following locations:

1. Path specified by the `PYPS_INVSIM_EXCEL_FILE` environment variable
2. Any Excel file in the `excel` directory that contains a table named "InvSim_Parameters"
3. Default path: `src/pyps_invsim/data/excel/PyPS_InvSim_v0.1.0.xlsm`

### Controlling Logging Output

You can control the verbosity of timing logs with the `--timing_logging_level` parameter:

```bash
# Using Bash
python -m src.pyps_invsim.simulations.level1_inventory_simulation --timing_logging_level detailed

# Using PowerShell
python -m src.pyps_invsim.simulations.level1_inventory_simulation --timing_logging_level detailed
```

Available logging levels:
- `off`: No timing information is displayed
- `minimal`: Only shows the total scenario completion time
- `normal`: Shows the scenario completion time and component timing breakdown (default)
- `detailed`: Shows the scenario completion time, component timing breakdown, and real-time component completion times

## Configuration

### Environment Variables

The package uses several environment variables to locate files and directories:

- `PYPS_INVSIM_ROOT`: Root directory of the project
- `PYPS_INVSIM_DATA`: Directory for data files
- `PYPS_INVSIM_EXCEL`: Directory for Excel files
- `PYPS_INVSIM_EXCEL_FILE`: Path to the Excel file with simulation parameters

You can set these variables to customize the package's behavior:

```bash
# Using Bash
export PYPS_INVSIM_EXCEL_FILE="/path/to/your/excel_file.xlsm"

# Using PowerShell
$env:PYPS_INVSIM_EXCEL_FILE="C:\path\to\your\excel_file.xlsm"
```

### Default Parameters

Default simulation parameters are stored in `config/default_parameters.yaml`. You can modify this file or provide your own parameters file.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.