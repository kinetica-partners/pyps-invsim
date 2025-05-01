"""
Excel dashboard utilities for inventory simulations.
"""
import os
import subprocess
from pathlib import Path
from typing import Optional

def insert_dashboard_image_to_excel(
    excel_file: str,
    image_path: str,
    table_name: str = "InvSim_Parameters",
    dashboard_sheet_name: str = "InvSim_Dashboard"
) -> bool:
    """
    Insert a dashboard image into an Excel file using VBScript.
    This approach works even when the Excel file is open.
    
    Args:
        excel_file: Path to the Excel file
        image_path: Path to the dashboard image
        table_name: Name of the parameters table (used to find the sheet if dashboard sheet doesn't exist)
        dashboard_sheet_name: Name of the dashboard sheet
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if image exists
        if not os.path.exists(image_path):
            print(f"Dashboard image not found: {image_path}")
            return False
        
        # Create a temporary VBScript file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        vbs_path = os.path.join(script_dir, "insert_image.vbs")
        
        # Convert paths to absolute paths
        excel_file = os.path.abspath(excel_file)
        image_path = os.path.abspath(image_path)
        
        # Write the VBScript
        with open(vbs_path, "w") as f:
            f.write(f"""
Option Explicit

Sub InsertDashboardImage()
    On Error Resume Next
    
    Dim xlApp, xlBook, xlSheet
    Dim sheetExists
    
    ' Open Excel
    Set xlApp = CreateObject("Excel.Application")
    xlApp.DisplayAlerts = False
    
    ' Try to open the workbook
    Set xlBook = xlApp.Workbooks.Open("{excel_file.replace('\\', '\\\\')}")
    
    If Err.Number <> 0 Then
        WScript.Echo "Error opening Excel file: " & Err.Description
        xlApp.Quit
        Set xlApp = Nothing
        WScript.Quit 1
    End If
    
    ' Check if {dashboard_sheet_name} sheet exists
    sheetExists = False
    Dim sheet
    For Each sheet In xlBook.Sheets
        If sheet.Name = "{dashboard_sheet_name}" Then
            sheetExists = True
            Exit For
        End If
    Next
    
    ' Create the sheet if it doesn't exist
    If Not sheetExists Then
        xlBook.Sheets.Add().Name = "{dashboard_sheet_name}"
    End If
    
    ' Get the dashboard sheet
    Set xlSheet = xlBook.Sheets("{dashboard_sheet_name}")
    
    ' Clear the sheet
    xlSheet.Cells.Clear
    
    ' Add a title
    xlSheet.Cells(1, 1).Value = "Inventory Simulation Dashboard"
    xlSheet.Cells(1, 1).Font.Size = 16
    xlSheet.Cells(1, 1).Font.Bold = True
    
    ' Delete any existing shapes (including images)
    Dim shp
    For Each shp In xlSheet.Shapes
        shp.Delete
    Next
    
    ' Insert the image
    xlSheet.Shapes.AddPicture "{image_path.replace('\\', '\\\\')}", False, True, xlSheet.Cells(3, 1).Left, xlSheet.Cells(3, 1).Top, 600, 400
    
    ' Save and close
    xlBook.Save
    xlBook.Close
    xlApp.Quit
    
    Set xlSheet = Nothing
    Set xlBook = Nothing
    Set xlApp = Nothing
    
    WScript.Echo "Dashboard image inserted successfully"
End Sub

' Run the main subroutine
InsertDashboardImage
""")
        
        # Run the VBScript
        result = subprocess.run(["cscript", "//NoLogo", vbs_path], capture_output=True, text=True)
        
        # Delete the temporary VBScript file
        os.remove(vbs_path)
        
        if result.returncode == 0:
            print(result.stdout.strip())
            return True
        else:
            print(f"Error running VBScript: {result.stderr.strip()}")
            return False
    
    except Exception as e:
        print(f"Error inserting dashboard image into Excel: {e}")
        return False