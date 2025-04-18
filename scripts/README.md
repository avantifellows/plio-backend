# Django Project Package Management

This directory contains scripts to help manage Python packages in this Django project.

## Usage

### Windows (PowerShell or Command Prompt)

Use `scripts\pip.bat` instead of `pip`:

```
scripts\pip install package_name
```

This will:
1. Install the package normally
2. Automatically update requirements.txt with the package and version

### For other pip commands

Any other pip commands work as normal:

```
scripts\pip list
scripts\pip freeze
scripts\pip uninstall package_name
```

## Important Notes

- Always use `scripts\pip install` instead of regular `pip install` to keep requirements.txt up to date
- These scripts must be run from the project root directory
- Share this setup with all team members to ensure consistent package management
