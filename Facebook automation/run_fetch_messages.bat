@echo off
setlocal
REM ---- đi tới thư mục của file .bat ----
cd /d "%~dp0"

REM ---- kích hoạt virtualenv (sửa đường dẫn nếu venv khác tên) ----
call ".\venv\Scripts\activate.bat"

REM ---- THAM SỐ CHỈNH Ở ĐÂY ----
set SINCE=2025-09-01
set UNTIL=2025-09-24
set OUT=inbox_sep.csv
set JSONL_OUT=inbox_sep.jsonl

REM ---- CHẠY SCRIPT ----
python fetch_page_messages.py ^
  --since %SINCE% ^
  --until %UNTIL% ^
  --out "%OUT%" ^
  --jsonl_out "%JSONL_OUT%"

echo.
echo [DONE] Output CSV : %OUT%
echo [DONE] Output JSONL: %JSONL_OUT%
pause
