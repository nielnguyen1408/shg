# Task Tracking — README

Tài liệu này để các GPT/Codex khác đọc/ghi task mà **không làm hỏng tiếng Việt** và **không dính lỗi UTF-8**.

## Mục đích & cấu trúc
- Bảng chính: `task_tracking.md` (Quick View + Task Details).
- Quick View: mỗi task cha một dòng, cột `Task | Status | Deadline | Priority | Owner | Link/Chat | Next Step | Last Update`.
- Task Details: mỗi task cha một mục với Goal, Status, Deadline, Priority, Owner, Links/Chat, Next step, Subtasks (đánh số 1, 1.1, 2, 2.1…), Notes. `Next step` luôn là subtask `[ ]` cần làm tiếp theo.

## Quy tắc cập nhật (bắt buộc)
- **Chỉ dùng `apply_patch`** để sửa file. Tuyệt đối không dùng `Add-Content`, `Set-Content`, hay lệnh PowerShell khác để ghi nội dung tiếng Việt.
- Giữ nguyên encoding **UTF-8** của file, không đổi sang encoding khác.
- Khi chỉnh text, thay đúng dòng/đúng khối bằng `apply_patch`; không chèn bằng lệnh append.

### Quy trình nhanh khi thêm/cập nhật task (để tránh lỗi lặt vặt)
1. (Một lần duy nhất sau khi tạo file) Kiểm tra UTF-8 bằng đoạn PowerShell ở cuối README; nếu `VALID_UTF8` → yên tâm patch thẳng, không cần re-check mỗi lần.
2. Thêm task mới:
   - Thêm dòng Quick View bằng `apply_patch`.
   - Thêm block Task Details theo mẫu bằng `apply_patch`.
3. Cập nhật task/subtask: sửa đúng block (tick `[x]`, đổi `Next step`, Status/Deadline/Notes…) bằng `apply_patch`.
4. Không dùng lệnh PowerShell `Add-Content`/`Set-Content` cho tiếng Việt; nếu bắt buộc phải script, dùng `python -c` với `PYTHONIOENCODING=utf-8` và regex rõ ràng.

### Thêm dòng Quick View
- Thêm một dòng mới trong bảng Quick View, đủ 8 cột.
- Ví dụ nội dung:  
  `| Campaign Tết 2026 | In progress | TBD | Medium | you | - | 1. Xác định goal & deliverables | pending |`

### Thêm block Task Details (mẫu)
```md
### Tên task
- **Goal**: …
- **Status**: In progress
- **Deadline**: …
- **Priority**: Medium
- **Owner**: you
- **Files/Dirs**: _(paths nếu có)_
- **Chat/Link**: _(URL nếu có)_
- **Next step**: 1. …

- **Subtasks**
  - [ ] **1.** …
  - [ ] **1.1** …
  - [ ] **2.** …

- **Notes**: _(blocker/bổ sung nếu có)_
```

### Cập nhật task/subtask
- Tick `[x]` khi hoàn thành; cập nhật `Next step` sang subtask tiếp theo.
- Điều chỉnh `Status` / `Deadline` / `Priority` / `Notes` nếu thay đổi.
- Nếu đổi nội dung dài, thay cả khối bằng `apply_patch`.

## Kiểm tra UTF-8 (PowerShell, so sánh byte)
Chạy từ thư mục gốc repo:
```powershell
$path = "C:\Users\namnp\Desktop\SHG all\Niel folder\task_tracking\task_tracking.md"  # đổi tên file cần kiểm tra
if (-not (Test-Path $path)) { "FILE_NOT_FOUND"; return }
$bytes = [IO.File]::ReadAllBytes($path)
$utf8  = [Text.Encoding]::UTF8
$decoded   = $utf8.GetString($bytes)
$reencoded = $utf8.GetBytes($decoded)
$eq = [System.Linq.Enumerable]::SequenceEqual($bytes, $reencoded)
if ($eq) { "VALID_UTF8" } else { "INVALID_UTF8" }
```
- **VALID_UTF8**: file sạch, dùng `apply_patch` bình thường.
- **INVALID_UTF8**: có byte lỗi. Cách xử lý nhanh:
  1) Tạo file mới, gõ tay một dòng tiếng Việt test.  
  2) `Save with Encoding… → UTF-8`.  
  3) Chỉ copy nội dung “sạch” vào (tránh copy từ file hỏng).  
  4) Kiểm tra lại đến khi ra `VALID_UTF8`.

## Lưu ý PowerShell/Python (tránh lỗi thường gặp)
- Không dùng here-string kiểu `python - <<'PY'` trong PowerShell (sẽ lỗi parser). Dùng `python -c "..."`.
- Đặt biến môi trường khi chạy Python để in Unicode:  
  `set PYTHONIOENCODING=utf-8` (PowerShell: `$env:PYTHONIOENCODING='utf-8'`).
- Nếu console hiển thị sai dấu: chạy `chcp 65001` trước khi `Get-Content` hoặc xem file trong VS Code.

## Lưu ý an toàn
- Không commit dữ liệu nhạy cảm (mật khẩu, token, PII).
- Ghi lại trao đổi quan trọng vào `Notes` hoặc thêm subtask mới nếu cần hành động cụ thể.
