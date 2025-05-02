"""
Helper module for imports that works in all environments.

This module ensures imports work correctly in three scenarios:
1. When running as an installed package (pip install pyps-invsim)
2. When running from src/pyps_invsim directly (cloned from GitHub)
3. When running from the development project (C:/PyPS-InvSim)
"""
import os
import sys
import importlib.util
from pathlib import Path

def setup_imports():
    """
    Set up imports to work in all environments:
    1. When running as an installed package
    2. When running from src/pyps_invsim directly
    3. When running from the development project
    """
    # Check if running as installed package
    if importlib.util.find_spec("pyps_invsim") is not None:
        # Package is installed, imports will work normally
        return
    
    # Get the current file's directory
    current_file = Path(__file__).resolve()
    current_dir = current_file.parent
    
    # Check if running from src/pyps_invsim directly
    if current_dir.parent.name == "pyps_invsim":
        # Add src to path
        src_dir = current_dir.parent.parent
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))
    
    # Check if running from development project
    else:
        # Find project root (where pyproject.toml is)
        current_path = current_dir
        while current_path != current_path.parent:
            if (current_path / "pyproject.toml").exists() or (current_path / ".git").exists():
                project_root = current_path
                break
            current_path = current_path.parent
        else:
            # If not found, use current directory's parent's parent's parent
            # This is a fallback for unusual directory structures
            project_root = current_dir.parent.parent.parent
        
        # Add src to path
        src_dir = project_root / "src"
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))