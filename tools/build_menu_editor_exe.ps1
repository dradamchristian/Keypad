param(
  [string]$PythonExe = "python",
  [string]$OutputName = "KeypadMenuEditor"
)

$ErrorActionPreference = "Stop"

& $PythonExe -m pip install --upgrade pyinstaller
& $PythonExe -m PyInstaller --onefile --name $OutputName menu_simulator.py

Write-Host "Built: dist/$OutputName.exe"
