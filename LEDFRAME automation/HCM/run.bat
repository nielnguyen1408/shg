@echo off
setlocal

REM Chuyen vao folder chua file .bat
cd /d "%~dp0"

REM Mo hop thoai chon file Excel bat dau tu thu muc hien tai
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $ofd = New-Object System.Windows.Forms.OpenFileDialog; $ofd.InitialDirectory = (Get-Item -Path '%cd%').FullName; $ofd.Filter = 'Excel files (*.xlsx)|*.xlsx|All files (*.*)|*.*'; if ($ofd.ShowDialog() -eq 'OK') { [Console]::Out.WriteLine($ofd.FileName) }"`) do set "INPUT_FILE=%%I"

if not defined INPUT_FILE (
  echo Khong chon file. Bam phim bat ky de thoat...
  pause >nul
  exit /b
)

REM Kiem tra python
where python >nul 2>nul && (set "PYTHON=python") || (set "PYTHON=py -3")

echo Dang chay bao cao cho: %INPUT_FILE%
%PYTHON% hcm_coverage_report.py --input "%INPUT_FILE%"
set "EC=%ERRORLEVEL%"

if not "%EC%"=="0" (
  echo Loi khi chay script. Ma loi: %EC%
) else (
  echo Hoan tat. File output se nam cung thu muc voi file input neu khong chi ro --output.
)

pause
