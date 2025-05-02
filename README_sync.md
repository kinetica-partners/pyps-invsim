# Syncing PyPS InvSim to GitHub

This document explains how to sync the PyPS InvSim package to a GitHub repository.

## Using the Sync Script

The package includes a Python script (`sync_to_github.py`) that automates the process of syncing the package to GitHub.

### Basic Usage

1. Navigate to the package directory:
   ```bash
   cd src/pyps_invsim
   ```

2. Run the sync script:
   ```bash
   python sync_to_github.py
   ```

   This will sync the package to the default repository: `https://github.com/kinetica-partners/pyps-invsim.git`

### Specifying a Different Repository

You can specify a different repository URL as a command-line argument:

```bash
python sync_to_github.py https://github.com/your-username/your-repo.git
```

### What the Script Does

The sync script:

1. Initializes a Git repository in the package directory (if one doesn't exist)
2. Sets up the remote repository URL
3. Adds all files in the package directory
4. Commits any changes
5. Pushes to the remote repository with the `-f` (force) flag for fast-forward

### Troubleshooting

If you encounter issues:

1. **Authentication errors**: Make sure you have the necessary permissions to push to the repository
2. **Branch issues**: The script tries to push to both `main` and `master` branches
3. **Git not found**: Ensure Git is installed and in your PATH

## Manual Syncing

If you prefer to sync manually:

1. Navigate to the package directory:
   ```bash
   cd src/pyps_invsim
   ```

2. Initialize a Git repository (if needed):
   ```bash
   git init
   ```

3. Add the remote repository:
   ```bash
   git remote add origin https://github.com/kinetica-partners/pyps-invsim.git
   ```

4. Add all files:
   ```bash
   git add .
   ```

5. Commit changes:
   ```bash
   git commit -m "Update PyPS InvSim package"
   ```

6. Push with fast-forward:
   ```bash
   git push -f origin main
   ```

## Syncing from the Main Project

If you're working in the main PyPS_InvSim project and want to sync just the package:

1. From the project root:
   ```bash
   cd src/pyps_invsim
   python sync_to_github.py
   ```

2. Or using Git subtree (from the project root):
   ```bash
   git subtree push --prefix=src/pyps_invsim https://github.com/kinetica-partners/pyps-invsim.git main