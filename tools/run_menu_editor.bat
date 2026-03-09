@echo off
setlocal

set EXE=%~dp0..\dist\KeypadMenuEditor.exe
if exist "%EXE%" (
  "%EXE%" %*
) else (
  echo KeypadMenuEditor.exe not found in dist\
  echo Build first with: powershell -ExecutionPolicy Bypass -File tools\build_menu_editor_exe.ps1
  exit /b 1
)
