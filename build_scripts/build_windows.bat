@echo off
echo === Building ROOT//X Windows Executable (.exe) ===
pip install pyinstaller

pyinstaller --onefile ^
  --name "rootx-toolkit.exe" ^
  --hidden-import "pypresence" ^
  --hidden-import "psutil" ^
  --hidden-import "colorama" ^
  --hidden-import "cryptography" ^
  --clean ^
  main.py

echo Build complete! Executable located at dist\rootx-toolkit.exe
pause
