import os, sys, argparse, time, json, csv
from typing import Iterator, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import requests

GRAPH_VERSION = os.getenv("FB_GRAPH_VERSION", "v17.0")
GRAPH_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"

# -------------------- Utils --------------------
def must_env(name: str) -> str:
    v = os.getenv(name, "").strip()
    if not v:
        print(f"[ERR] Thiếu biến môi trường: {name}")
        sys.exit(1)
    return v

def parse_date_start(s: str) -> datetime:
    """YYYY-MM-DD -> 00:00:00 UTC; ISO có giờ -> giữ nguyên, quy về UTC."""
    try:
        dt = datetime.fromisoformat(s)
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        dt = datetime.strptime(s, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)

def parse_date_end(s: str) -> datetime:
    """YYYY-MM-DD -> 23:59:59.999999 UTC; ISO có giờ -> giữ nguyên, quy về UTC."""
    try:
        dt = datetime.fromisoformat(s)
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        d0 = datetime.strptime(s, "%Y-%m-%d")
        return (d0 + timedelta(days=1) - timedelta(microseconds=1)).replace(tzinfo=timezone.utc)

def to_unix(dt: datetime) -> int:
    return int(dt.timestamp())

def hr_num(n: int) -> str:
    return f"{n:,}"

def http_get(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.get(url, params=params, timeout=30)
    try:
        data = r.json()
    except Exception:
        raise RuntimeError(f"Invalid JSON from Graph: {r.text[:300]}")
    if "error" in data:
        raise RuntimeError(json.dumps(data["error"], ensure_ascii=False))
    return data

def parse_fb_ts(ts: str) -> datetime:
    # "YYYY-MM-DDTHH:MM:SS+0000" -> UTC
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z").astimezone(timezone.utc)

# -------------------- Paging (optimized) --------------------
def iter_conversations_earlystop(
    page_id: str,
    page_token: str,
    since_dt_utc: datetime,
    limit_conversations: Optional[int] = None
) -> Iterator[Dict[str, Any]]:
    """
    Duyệt conversations (mới -> cũ) và dừng hẳn khi updated_time < since_dt_utc.
    """
    url = f"{GRAPH_URL}/{page_id}/conversations"
    params = {
        "fields": "id,updated_time,link,participants.limit(25){id,name}",
        "limit": 50,
        "access_token": page_token,
    }
    fetched = 0
    while True:
        data = http_get(url, params)
        convs = data.get("data", [])
        if not convs:
            return
        for c in convs:
            fetched += 1
            upd = parse_fb_ts(c["updated_time"])
            if upd < since_dt_utc:
                return  # early stop: phần sau cũ hơn nữa, bỏ
            yield c
            if limit_conversations and fetched >= limit_conversations:
                return
        next_url = data.get("paging", {}).get("next")
        if not next_url:
            break
        url, params = next_url, {}  # next đã chứa token & paging

def has_messages_in_range(conv_id: str, page_token: str, since_unix: int, until_unix: int) -> bool:
    """
    Đầu dò nhẹ: /messages?limit=1 trong range. Có => True; không => False.
    """
    url = f"{GRAPH_URL}/{conv_id}/messages"
    params = {
        "fields": "id,created_time",
        "limit": 1,
        "access_token": page_token,
        "since": since_unix,
        "until": until_unix,
    }
    data = http_get(url, params)
    return len(data.get("data", [])) > 0

def iter_messages(conv_id: str, page_token: str, since_unix: int, until_unix: int) -> Iterator[Dict[str, Any]]:
    """
    Tải message trong range ngay từ API.
    """
    url = f"{GRAPH_URL}/{conv_id}/messages"
    params = {
        "fields": "id,from,to,message,created_time",
        "limit": 100,
        "access_token": page_token,
        "since": since_unix,
        "until": until_unix,
    }
    while True:
        data = http_get(url, params)
        for m in data.get("data", []):
            yield m
        next_url = data.get("paging", {}).get("next")
        if not next_url:
            break
        url, params = next_url, {}

# -------------------- Writers (append-safe) --------------------
class CSVWriter:
    def __init__(self, out_path: str):
        self.out_path = out_path
        self.header = [
            "conversation_id", "conversation_link", "participants",
            "message_id", "created_time_utc", "from_id", "from_name",
            "to_ids", "message"
        ]
        self._ensure_header()

    def _ensure_header(self):
        need_header = not os.path.exists(self.out_path) or os.path.getsize(self.out_path) == 0
        if need_header:
            with open(self.out_path, "w", encoding="utf-8", newline="") as f:
                csv.writer(f).writerow(self.header)

    def append(self, row: Dict[str, Any]):
        with open(self.out_path, "a", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow([row.get(k, "") for k in self.header])

class JSONLWriter:
    def __init__(self, out_path: Optional[str]):
        self.out_path = out_path

    def append(self, obj: Dict[str, Any]):
        if not self.out_path:
            return
        with open(self.out_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

# -------------------- Main --------------------
def main():
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", required=True, help="YYYY-MM-DD hoặc ISO (UTC nếu không timezone)")
    parser.add_argument("--until", required=True, help="YYYY-MM-DD hoặc ISO (UTC nếu không timezone)")
    parser.add_argument("--out", default="page_messages.csv", help="CSV output (append-safe)")
    parser.add_argument("--jsonl_out", default=None, help="Nếu set, xuất JSONL song song (append-safe)")
    parser.add_argument("--limit_conversations", type=int, default=None, help="Chỉ lấy N hội thoại đầu (debug)")
    parser.add_argument("--progress_every", type=int, default=10, help="In tiến trình mỗi N hội thoại")
    args = parser.parse_args()

    page_id = must_env("PAGE_ID")
    page_token = must_env("PAGE_ACCESS_TOKEN")

    dt_since = parse_date_start(args.since)
    dt_until = parse_date_end(args.until)
    if dt_since > dt_until:
        print("[ERR] --since phải <= --until")
        sys.exit(1)

    since_unix = to_unix(dt_since)
    until_unix = to_unix(dt_until)

    print(f"[INFO] Page: {page_id}")
    print(f"[INFO] Range (UTC): {dt_since.isoformat()}  →  {dt_until.isoformat()}")
    print(f"[INFO] API filter: since={since_unix}, until={until_unix}")
    print(f"[INFO] Output CSV : {args.out}")
    if args.jsonl_out:
        print(f"[INFO] Output JSONL: {args.jsonl_out}")

    csv_writer = CSVWriter(args.out)
    jsonl_writer = JSONLWriter(args.jsonl_out)

    total_convos = 0
    total_msgs = 0
    t0 = time.time()

    try:
        for convo in iter_conversations_earlystop(page_id, page_token, dt_since, args.limit_conversations):
            total_convos += 1
            conv_id = convo["id"]

            # Precheck: bỏ qua hội thoại không có message trong khoảng
            if not has_messages_in_range(conv_id, page_token, since_unix, until_unix):
                if total_convos % max(1, args.progress_every) == 0:
                    elapsed = time.time() - t0
                    rate = total_convos / elapsed if elapsed > 0 else 0
                    print(f"[PROGRESS] Conversations: {hr_num(total_convos)} | Messages: {hr_num(total_msgs)} | {rate:.2f} conv/s | Elapsed: {elapsed:.1f}s")
                continue

            link = convo.get("link", "")
            participants = ", ".join([p.get("name","") for p in (convo.get("participants", {}) or {}).get("data", [])])

            msg_added = 0
            for msg in iter_messages(conv_id, page_token, since_unix, until_unix):
                # Lọc lớp 2 ở client (chặn mọi message ngoài range)
                dt_msg = parse_fb_ts(msg.get("created_time", ""))
                if dt_msg < dt_since or dt_msg > dt_until:
                    # Có thể log cảnh báo nếu cần:
                    # print(f"[WARN] Ngoài range: {dt_msg.isoformat()} in {conv_id} -> skip")
                    continue

                to_ids = ",".join([t.get("id","") for t in (msg.get("to") or {}).get("data", [])]) if msg.get("to") else ""
                row = {
                    "conversation_id": conv_id,
                    "conversation_link": link,
                    "participants": participants,
                    "message_id": msg.get("id",""),
                    "created_time_utc": dt_msg.isoformat(),
                    "from_id": (msg.get("from") or {}).get("id",""),
                    "from_name": (msg.get("from") or {}).get("name",""),
                    "to_ids": to_ids,
                    "message": msg.get("message",""),
                }
                csv_writer.append(row)
                jsonl_writer.append(row)
                total_msgs += 1
                msg_added += 1

            if msg_added > 0:
                print(f"[INFO] {conv_id}: +{msg_added} msg(s) trong range")

            if total_convos % max(1, args.progress_every) == 0:
                elapsed = time.time() - t0
                rate = total_convos / elapsed if elapsed > 0 else 0
                print(f"[PROGRESS] Conversations: {hr_num(total_convos)} | Messages: {hr_num(total_msgs)} | {rate:.2f} conv/s | Elapsed: {elapsed:.1f}s")

    except KeyboardInterrupt:
        print("\n[WARN] Dừng theo yêu cầu (Ctrl+C). Dữ liệu đã ghi an toàn đến thời điểm dừng.")
    except Exception as e:
        print("\n[FAIL] Lỗi Graph API:", e)
        print("      Kiểm tra: PAGE ACCESS TOKEN + scopes: pages_messaging, pages_read_engagement, pages_manage_metadata")
        sys.exit(1)

    elapsed = time.time() - t0
    print(f"\n[DONE] Conversations duyệt: {hr_num(total_convos)} | Messages ghi: {hr_num(total_msgs)} | Elapsed: {elapsed:.1f}s")
    print(f"[OUT] CSV : {args.out}")
    if args.jsonl_out:
        print(f"[OUT] JSONL: {args.jsonl_out}")

if __name__ == "__main__":
    main()
