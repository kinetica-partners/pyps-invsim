#!/usr/bin/env python
"""
Script to sync the PyPS InvSim package to GitHub.
This script pushes the package to a new GitHub repository with fast-forward.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(command, cwd=None):
    """Run a shell command and return the output."""
    print(f"Running: {command}")
    result = subprocess.run(
        command,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False, result.stderr
    
    return True, result.stdout


def sync_to_github(package_dir, repo_url):
    """Sync the package to GitHub with fast-forward."""
    # Ensure we're in the package directory
    os.chdir(package_dir)
    print(f"Working directory: {os.getcwd()}")
    
    # Check if .git directory exists
    if not os.path.exists(".git"):
        print("Initializing new git repository...")
        success, output = run_command("git init")
        if not success:
            return False
    
    # Check if the remote exists
    success, output = run_command("git remote -v")
    if success:
        if "origin" in output:
            print("Updating existing origin remote...")
            success, _ = run_command(f"git remote set-url origin {repo_url}")
        else:
            print("Adding origin remote...")
            success, _ = run_command(f"git remote add origin {repo_url}")
    
    # Add all files
    print("Adding files...")
    success, _ = run_command("git add .")
    if not success:
        return False
    
    # Commit if there are changes
    print("Committing changes...")
    success, output = run_command('git commit -m "Update PyPS InvSim package"')
    
    # Push with fast-forward
    print("Pushing to GitHub with fast-forward...")
    success, output = run_command("git push -f origin main")
    if not success:
        # Try pushing to master branch if main fails
        print("Trying master branch...")
        success, output = run_command("git push -f origin master")
    
    if success:
        print("Successfully pushed to GitHub!")
        return True
    else:
        print("Failed to push to GitHub.")
        return False


if __name__ == "__main__":
    # Get the package directory (where this script is located)
    package_dir = Path(__file__).parent.absolute()
    
    # Default GitHub repository URL
    default_repo_url = "https://github.com/kinetica-partners/pyps-invsim.git"
    
    # Get repository URL from command line or use default
    repo_url = sys.argv[1] if len(sys.argv) > 1 else default_repo_url
    
    print(f"Syncing package to: {repo_url}")
    success = sync_to_github(package_dir, repo_url)
    
    if success:
        print("Sync completed successfully!")
    else:
        print("Sync failed. Please check the error messages above.")
        sys.exit(1)