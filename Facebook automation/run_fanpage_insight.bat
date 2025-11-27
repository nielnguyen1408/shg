@echo off
setlocal enabledelayedexpansion

REM ====== THÔNG SỐ BẠN ĐIỀN Ở ĐÂY ======
set FB_APP_ID=123456789012345
set FB_APP_SECRET=abc123xyzSECRET
set FB_USER_TOKEN=EAAB-user-token-OPTIONAL
set PAGE_ID=112233445566778
set PAGE_ACCESS_TOKEN=EAAB-page-access-token-RECOMMENDED
set FB_GRAPH_VERSION=v19.0

set POST_ID=112233445566778_9988776655443322
REM Nếu chỉ có post suffix (vd 9988776655443322) bạn có thể set POST_ID=9988776655443322
REM Script sẽ tự ghép thành {PAGE_ID}_{suffix} nếu cần.

set SINCE=2025-09-01
set UNTIL=2025-09-25
set METRICS=post_impressions,post_impressions_unique,post_engaged_users,post_clicks,post_reactions_by_type_total
set OUT_XLSX=post_insights.xlsx
REM =====================================

REM (Tuỳ chọn) kích hoạt venv nếu có
if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
)

REM (Lần đầu) cài thư viện cần thiết
REM pip install -q requests openpyxl

py -3 fb_post_insights.py ^
  --app-id "%FB_APP_ID%" ^
  --app-secret "%FB_APP_SECRET%" ^
  --user-token "%FB_USER_TOKEN%" ^
  --page-id "%PAGE_ID%" ^
  --page-token "%PAGE_ACCESS_TOKEN%" ^
  --graph-version "%FB_GRAPH_VERSION%" ^
  --post-id "%POST_ID%" ^
  --since "%SINCE%" ^
  --until "%UNTIL%" ^
  --metrics "%METRICS%" ^
  --out-xlsx "%OUT_XLSX%"

if errorlevel 1 (
  echo [FAIL] Loi khi chay script. Code %errorlevel%
  exit /b %errorlevel%
)

echo [OK] Da tao file: %OUT_XLSX%
endlocal
