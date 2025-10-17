# Environment Setup

Follow these steps to prepare a local development environment for AHS Diagnostic Parser (AHSDP).

## Requirements
- Python 3.11 recommended (3.9 minimum)
- PowerShell (Windows) or bash/zsh (macOS/Linux)
- Git (optional, for source control)

## 1. Create a Virtual Environment
```powershell
python -m venv .venv
```
On macOS/Linux, you can run the same command from bash.

## 2. Activate the Environment
```powershell
.\.venv\Scripts\Activate.ps1
```
For Command Prompt:
```cmd
.\.venv\Scripts\activate.bat
```
For bash/zsh on macOS/Linux:
```bash
source .venv/bin/activate
```

## 3. Upgrade Packaging Tooling
```powershell
python -m pip install --upgrade pip setuptools wheel
```

## 4. Install Project Dependencies
- CLI only:
  ```powershell
  python -m pip install -e .
  ```
- CLI + GUI:
  ```powershell
  python -m pip install -e ".[gui]"
  ```

## 5. Verify Installation
```powershell
python -c "import ahsdp; print(ahsdp.__version__)"
python -m ahsdp.cli --help
ahsdp --help
```

If you plan to use the GUI:
```powershell
python -m ahsdp.gui
```

## Tips
- Re-run the activation command whenever you open a new shell.
- Use `python -m pip list` to confirm PySimpleGUI is installed when GUI support is required.
- Deactivate the environment with `deactivate` when you are done.
