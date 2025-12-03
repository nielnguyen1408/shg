@echo off
cd /d %~dp0

for /f "usebackq tokens=*" %%i in (`powershell -command "Add-Type -AssemblyName System.Windows.Forms; $f = New-Object System.Windows.Forms.OpenFileDialog; $f.Filter = 'Excel Files (*.xlsx)|*.xlsx'; if($f.ShowDialog() -eq 'OK'){Write-Output $f.FileName}"`) do set "userfile=%%i"

python vn_clean_and_split4_v2.py "%userfile%"

pause