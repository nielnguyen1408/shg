# Seeding Knowledge Exporter (Auto-generate .md from approved_comments)

> File này để **đặt trong Knowledge**. Khi GPT có **Code Interpreter + File Upload** bật, hãy làm đúng quy trình dưới đây để **đọc `approved_comments.*` và xuất file giọng điệu (.md)**.

---

## Cách dùng nhanh
1) Upload `approved_comments.csv` hoặc `.json` vào chat.
2) Nói: **“Xuất knowledge tên: Seeding điều hướng branding”** (hoặc tên khác).
3) Trợ lý phải set biến tên và **chạy khối Python bên dưới** không hỏi lại.
4) Tải file kết quả, ví dụ: `seeding_dieu_huong_branding.md`, và upload vào Knowledge cho các phiên sau.

> Nếu bạn không đưa tên, mặc định lưu: `seeding_knowledge.md`.

---

## Quy tắc an toàn
- Chỉ dùng cho seeding marketing hợp pháp, nội dung tích cực.
- Không PII, không nguyên văn dài; ví dụ minh họa ≤120 ký tự, rút gọn.
- Không khẳng định chất lượng ngoài phạm vi văn phong.

---

## Khối PYTHON phải chạy (nguyên khối, không dùng internet)

```python
import os, re, json, math, unicodedata
import pandas as pd
from pathlib import Path
from collections import Counter

def to_stub(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c)!='Mn')
    s = re.sub(r'[^a-zA-Z0-9]+','_', s.strip().lower()).strip('_')
    return s or "seeding_knowledge"

# Detect input file (ưu tiên tên chứa 'approved')
cands = [p for p in Path('.').glob('*') if p.is_file() and p.suffix.lower() in ('.csv','.json')]
if not cands:
    raise SystemExit("Không thấy file CSV/JSON. Hãy upload 'approved_comments' trước.")
target = sorted(cands, key=lambda p: ('approved' not in p.name.lower(), p.name))[0]

# Read to DataFrame
if target.suffix.lower()=='.csv':
    df = pd.read_csv(target)
else:
    df = pd.DataFrame(json.load(open(target, 'r', encoding='utf-8')))

if 'content' not in df.columns:
    raise SystemExit("Thiếu cột 'content' trong dữ liệu.")

# Clean & sample
texts = [str(x).strip() for x in df['content'].fillna('') if str(x).strip()]
texts = list(dict.fromkeys(texts))[:2000]  # hạn mức an toàn

# Tokenize
def toks(s): 
    s = re.sub(r'\s+',' ',s.lower()).strip()
    return re.findall(r"[a-zA-ZÀ-ỹ0-9_]+|[!?]", s)

STOP = set("tôi toi bạn ban mình minh chúng ta là thì và của một những đã đang sẽ trong trên dưới này kia đây ấy các cho không ko đâu nữa khi nếu vì nên bị được từ".split())
docs = [[t for t in toks(x) if re.match(r"^[a-zA-ZÀ-ỹ0-9_]+$",t) and t not in STOP] for x in texts]

# Metrics
avg_len = round(sum(len(toks(x)) for x in texts)/max(1,len(texts)),2)
exclam = sum(x.count('!') for x in texts)/max(1,len(texts))
quest  = sum(x.count('?') for x in texts)/max(1,len(texts))
emoji  = sum(len(re.findall(r"[🙂😊😁😄👍🔥✨❤️👌🤝🙌🎉]", x)) for x in texts)/max(1,len(texts))

# crude tf-idf-ish
from collections import Counter
dfreq = Counter()
for ws in docs: 
    for w in set(ws): dfreq[w]+=1
N=len(docs)
scores=Counter()
for ws in docs:
    tf=Counter(ws)
    L=len(ws) or 1
    for w,f in tf.items():
        scores[w]+= (f/L)*math.log(1+N/(1+dfreq[w]))
uni = [w for w,_ in scores.most_common(15)]

def ngrams(ws,n): 
    return [" ".join(ws[i:i+n]) for i in range(len(ws)-n+1)]
bg = Counter(w for ws in docs for w in ngrams(ws,2)).most_common(10)
tg = Counter(w for ws in docs for w in ngrams(ws,3)).most_common(8)

# Persona heuristics
persona=[]
persona.append("Giọng tự nhiên, tích cực" if emoji+exclam>0.2 else "Trung tính, tiết chế")
persona.append("Câu ngắn–trung bình, dễ đọc" if avg_len<25 else "Câu trung bình–dài, có diễn giải")
if emoji>0.2: persona.append("Dùng emoji mức vừa")
if exclam>0.2: persona.append("Nhấn nhá cảm thán")
if quest>0.15: persona.append("Có câu hỏi gợi mở")

# Patterns + examples
def patternize(s):
    s=re.sub(r"\s+"," ",s).strip()
    s=re.sub(r"\b(mình|tôi|bạn|mọi người)\b","[xưng hô]",s,flags=re.I)
    s=re.sub(r"\b(thương hiệu|sản phẩm|dịch vụ)\b","[đối tượng]",s,flags=re.I)
    s=re.sub(r"\b(ban đầu|lúc đầu)\b","[mở hoài nghi]",s,flags=re.I)
    s=re.sub(r"\b(nhưng|rồi)\b","[chuyển ý]",s,flags=re.I)
    return s[:120]

patterns=[]
for s in texts:
    p=patternize(s)
    if 8<=len(p)<=120 and p not in patterns:
        patterns.append(p)
    if len(patterns)>=8: break

if not patterns:
    patterns=["[xưng hô] thấy [đối tượng] khá ổn, trải nghiệm vượt kỳ vọng.",
              "Ban đầu hơi lăn tăn [chuyển ý] dùng rồi mới hiểu vì sao được khen."]

examples=[]
for s in texts:
    s=re.sub(r"\s+"," ",s).strip()
    s=s[:120]
    if len(s)>=15 and s not in examples:
        examples.append(s)
    if len(examples)>=10: break

# Naming from user-provided vars (assistant phải set trước khi chạy nếu người dùng đặt tên)
try:
    title = user_name_title
    stub  = user_name_stub
except NameError:
    title = "Seeding knowledge"; stub="seeding_knowledge"

# Render .md
md = ["# "+title, "", "## Persona", ", ".join(persona), "", "## Tone patterns"]
md += [f"- {p}" for p in patterns]
md += ["", "## Keyword clusters",
       "- Unigram: "+", ".join(uni),
       "- Bigram: "+", ".join([w for w,_ in bg]),
       "- Trigram: "+", ".join([w for w,_ in tg]),
       "", "## Sentiment summary",
       f"- Độ dài TB (token): {avg_len}",
       f"- Emoji/cmt: {round(emoji,3)}",
       f"- Cảm thán/cmt: {round(exclam,3)}",
       f"- Câu hỏi/cmt: {round(quest,3)}",
       "", "## Style constraints",
       "- Tránh PR thô, so sánh công kích.",
       "- Ưu tiên câu ngắn, trải nghiệm cá nhân.",
       "- Emoji ở mức phù hợp bối cảnh.",
       "", "## Recommendations",
       "- Giữ ngôn ngữ đời thường, có 'độ thật'.",
       "- Dùng chuyển ý “ban đầu… nhưng…” khi hợp lý.",
       "- Gợi câu hỏi nhẹ để mở thảo luận.",
       "- Tận dụng từ khóa chủ đạo một cách tự nhiên.",
       "", "## Example lines"]
md += [f"- {e}" for e in examples]

out = Path(f"/mnt/data/{stub}.md")
out.write_text("\n".join(md), encoding="utf-8")
out
```

---

## Macro hội thoại
- “**Xuất knowledge tên: Seeding điều hướng branding**” → trợ lý set:  
  `user_name_title = "Seeding điều hướng branding"`  
  `user_name_stub  = "seeding_dieu_huong_branding"`  
  rồi chạy khối Python, trả link:  
  `sandbox:/mnt/data/seeding_dieu_huong_branding.md`

- “**Liệt kê knowledge đã tạo**” → liệt kê tất cả file `.md` trong `/mnt/data`.

- “**Gộp knowledge A + B thành C**” → đọc 2 file `.md`, hợp nhất Persona/Patterns/Keywords/Recommendations, lưu `C.md`.


# --- JSON phẳng (không lồng) ---
flat = {
    "title": title,
    "persona": "; ".join(persona),
    "tone_patterns": " | ".join(patterns),
    "unigram_keywords": ", ".join(uni),
    "bigram_keywords": ", ".join([w for w,_ in bg]),
    "trigram_keywords": ", ".join([w for w,_ in tg]),
    "avg_token_length": avg_len,
    "emoji_per_comment": round(emoji,3),
    "exclaim_per_comment": round(exclam,3),
    "question_per_comment": round(quest,3),
    "style_constraints": "Tránh PR thô; Ưu tiên câu ngắn, trải nghiệm; Emoji vừa phải",
    "recommendations": "Giữ ngôn ngữ đời thường; Dùng chuyển ý 'ban đầu… nhưng…'; Gợi câu hỏi nhẹ; Dùng keyword tự nhiên",
    "example_lines": " | ".join(examples)
}
json_path = Path(f"/mnt/data/{stub}_flat.json")
json_path.write_text(json.dumps(flat, ensure_ascii=False, indent=2), encoding="utf-8")

# --- Excel tổng hợp ---
excel_path = Path(f"/mnt/data/{stub}.xlsx")
with pd.ExcelWriter(excel_path, engine="xlsxwriter") as writer:
    pd.DataFrame([flat]).to_excel(writer, index=False, sheet_name="Summary")
    df.to_excel(writer, index=False, sheet_name="ApprovedComments")
    pd.DataFrame({"tone_patterns": patterns}).to_excel(writer, index=False, sheet_name="Patterns")
    pd.DataFrame({"unigram": uni}).to_excel(writer, index=False, sheet_name="Keywords-Uni")
    pd.DataFrame({"bigram": [w for w,_ in bg]}).to_excel(writer, index=False, sheet_name="Keywords-Bi")
    pd.DataFrame({"trigram": [w for w,_ in tg]}).to_excel(writer, index=False, sheet_name="Keywords-Tri")

import json, pandas as pd
from pathlib import Path
from datetime import datetime

# === INPUT giả lập (GPT sẽ thay bằng dữ liệu thật từ người dùng) ===
input_data = {
  "bai_viet_goc": "Thương hiệu ABC vừa ra mắt dòng sản phẩm skincare mới...",
  "dinh_huong": ["Nhấn mạnh độ an toàn", "Tập trung trải nghiệm thực tế người dùng"],
  "tone": "tự nhiên",
  "mood": "tích cực",
  "so_luong": 10,
  "do_dai_tb": 2,
  "yeu_cau_khac": "có emoji, xen lẫn vài bình luận phản hồi qua lại"
}

# === Sinh comment mẫu (GPT sinh thật ở runtime) ===
comments = [
  "Dòng này mình dùng thử thấy dịu nhẹ thật, da nhạy cảm vẫn ổn 😊",
  "Ban đầu không tin mấy quảng cáo đâu, mà dùng rồi phải công nhận chất lượng tốt.",
  "Chai thiết kế xinh mà mùi dễ chịu, đáng đồng tiền.",
  "Đọc bài này xong mới biết hãng có quy trình kiểm định rõ ràng vậy luôn 🔥",
  "Ai dùng rồi chia sẻ thêm cảm nhận với, mình đang cân nhắc mua 😅",
  "Thấy ai review cũng khen, chắc phải thử một chai xem sao.",
  "Điểm cộng là không bị kích ứng, da mình yếu mà vẫn dùng được.",
  "Đúng kiểu skincare dành cho người lười mà vẫn muốn đẹp 😁",
  "Thương hiệu này làm nội dung lúc nào cũng gần gũi, dễ tin.",
  "Cảm ơn bài chia sẻ, đọc mà muốn chăm sóc bản thân hơn luôn!"
]

# === Tạo dữ liệu phẳng ===
flat_records = []
for i, c in enumerate(comments, 1):
    flat_records.append({
        "id": i,
        "comment": c,
        "tone": input_data["tone"],
        "mood": input_data["mood"],
        "source_post": input_data["bai_viet_goc"][:100] + "...",
        "dinh_huong": "; ".join(input_data["dinh_huong"]),
        "extra": input_data.get("yeu_cau_khac", "")
    })

# === Xuất JSON phẳng ===
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
json_path = Path(f"/mnt/data/seeding_output_{timestamp}.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(flat_records, f, ensure_ascii=False, indent=2)

# === Xuất Excel ===
excel_path = Path(f"/mnt/data/seeding_output_{timestamp}.xlsx")
pd.DataFrame(flat_records).to_excel(excel_path, index=False, sheet_name="SeedingComments")

(json_path, excel_path)
