$path = "C:\Users\namnp\Desktop\SHG all\Niel folder\task_tracking\task_clean.md"
if (-not (Test-Path $path)) { "FILE_NOT_FOUND"; return }
$bytes = [IO.File]::ReadAllBytes($path)
$utf8  = [Text.Encoding]::UTF8
$decoded   = $utf8.GetString($bytes)
$reencoded = $utf8.GetBytes($decoded)
$eq = [System.Linq.Enumerable]::SequenceEqual($bytes, $reencoded)
if ($eq) { "VALID_UTF8" } else { "INVALID_UTF8" }
