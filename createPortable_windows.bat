REM rd /S /Q dist
REM rd /S /Q build

pyinstaller createPortable_windows.spec
iscc /q packaging_windows\setup.iss