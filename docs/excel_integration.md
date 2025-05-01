# Excel Integration for PyPS InvSim

This document explains how to integrate the PyPS InvSim package with Microsoft Excel, allowing you to run simulations directly from your Excel workbook.

## Adding the VBA Module to Excel

1. Open your Excel workbook (e.g., `PyPS_InvSim_v0.1.0.xlsm`)
2. Press `Alt + F11` to open the VBA Editor
3. In the VBA Editor, right-click on your workbook in the Project Explorer and select `Import File...`
4. Navigate to the `src/pyps_invsim/utils/InvSim_Runner.bas` file and click `Open`
5. Save your workbook as a macro-enabled file (`.xlsm`)

## Using the VBA Module

The VBA module provides a simple function to run the inventory simulation from Excel:

### Basic Functions

- `RunSimulation()`: Runs the simulation using the current Excel file as input

### Adding a Button to Your Worksheet

The module includes a function to add a button to your worksheet:

- `AddRunButton()`: Adds a simple "Run Simulation" button to the active sheet

To add a button:

1. Open your Excel workbook
2. Press `Alt + F8` to open the Macro dialog
3. Select `AddRunButton` and click `Run`
4. The button will be added to the active sheet

## Configuration

By default, the module assumes:

1. Python is in your system PATH (command: `python`)
2. The script file is located in one of these locations relative to your Excel file:
   - `[Excel folder]\src\pyps_invsim\simulations\level1_inventory_simulation.py`
   - `[Excel folder]\pyps_invsim\simulations\level1_inventory_simulation.py`
   - `[Excel folder]\..\src\pyps_invsim\simulations\level1_inventory_simulation.py`
   - `[Excel folder]\..\pyps_invsim\simulations\level1_inventory_simulation.py`
   - `[Excel folder]\simulations\level1_inventory_simulation.py`
   - `[Excel folder]\level1_inventory_simulation.py`

The VBA module will automatically search for the script in these locations.

If you need to change the Python path, you can modify the VBA code directly:

```vba
' In the RunSimulation() function:
pythonPath = "C:\path\to\python.exe"  ' Change to your Python path
```

### How It Works

The VBA module:
1. Gets the path of your Excel workbook
2. Searches for the Python script in several common locations relative to the Excel file
3. Runs the script with your Excel file as input
4. Displays a success message or an error message with debugging information

## Example: Running from a Button

1. Add a button to your worksheet using `AddRunButton()`
2. Click the button to run the simulation
3. The simulation will use the parameters from the `InvSim_Parameters` table in your workbook
4. Results will be displayed in the console and optionally inserted back into Excel

## Troubleshooting

If you encounter issues:

1. **Python not found (Error code 2)**: Make sure Python is installed and in your PATH, or edit the VBA code to set the full path to your Python executable
2. **Script not found (Error code 2)**: The VBA module couldn't find the Python script. Check the Debug.Print output in the VBA Immediate window (Ctrl+G in the VBA Editor) to see which paths were searched.
3. **Excel file path issues**: Make sure your Excel file is saved before running the simulation
4. **Permission issues**: Run Excel as administrator if you encounter permission problems
5. **Import errors**: If you see Python import errors, make sure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```
6. **Manually specifying the script path**: If the automatic path detection doesn't work, you can modify the VBA code to specify the exact path:
   ```vba
   ' In the RunSimulation() function, replace:
   scriptPath = FindScriptPath(workbookDir)
   
   ' With:
   scriptPath = "C:\exact\path\to\level1_inventory_simulation.py"
   ```

## Advanced: Customizing the VBA Module

You can modify the VBA module to add more functionality:

1. Open the VBA Editor (`Alt + F11`)
2. Navigate to the `InvSim_Runner` module
3. Add or modify the code as needed

For example, you could add command-line arguments to:
- Specify the number of scenarios
- Change logging levels
- Control visualization options