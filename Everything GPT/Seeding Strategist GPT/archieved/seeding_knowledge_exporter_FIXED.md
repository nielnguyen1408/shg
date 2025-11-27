# Seeding Knowledge Exporter (Auto .md + flat JSON + Excel + Labeled Comments)
> Đặt file này trong **Knowledge**. Bật **Code Interpreter + File Upload**.
> Quy trình:
> 1) Upload `approved_comments.csv` hoặc `.json`
> 2) Nói: **“Xuất knowledge tên: <Tên bạn muốn>”**
> 3) Trợ lý set biến tên và **chạy khối Python duy nhất** ở dưới.
> 4) Kết quả: `<stub>.md` (Knowledge), `<stub>_flat.json` (summary phẳng), `<stub>.xlsx` (đầy đủ), cộng thêm **bảng gán nhãn từng comment** với 2 cột mới: `muc_dich`, `chien_thuat`.
>
> Taxonomy mặc định (có thể chỉnh trong code):
> - `muc_dich`: kích hoạt thảo luận | xác nhận uy tín | chia sẻ trải nghiệm | phản biện nhẹ | khuếch đại cảm xúc | chốt hạ mua hàng | định hướng thương hiệu | hài hước / giải trí
> - `chien_thuat`: hỏi gợi mở | cảm thán tích cực | so sánh nhẹ | chuyển ý tự nhiên | truyền cảm hứng | hài hước nhẹ | đồng cảm cá nhân | đề xuất / khuyến nghị

---

## KHỐI PYTHON DUY NHẤT (chạy nguyên khối, không internet)
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
texts = list(dict.fromkeys(texts))[:5000]  # hạn mức an toàn

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

# ---------- Heuristic labeling for each original comment ----------
def label_purpose(text):
    t = text.lower()
    if "?" in t or any(k in t for k in ["ai dùng", "có ai", "không nhỉ", "không?", "nhỉ?"]):
        return "kích hoạt thảo luận"
    if any(k in t for k in ["quy trình", "kiểm định", "chính hãng", "bảo hành", "chứng nhận", "nguồn gốc"]):
        return "xác nhận uy tín"
    if any(k in t for k in ["ban đầu", "lúc đầu", "nghĩ", "tưởng", "nhưng"]):
        return "phản biện nhẹ"
    if any(k in t for k in ["mua", "đặt", "thử", "phải thử", "chốt", "rinh"]):
        return "chốt hạ mua hàng"
    if any(emo in t for emo in ["😊","😁","😄","👍","🔥","✨","❤️","👌","🤝","🙌","🎉"]):
        return "khuếch đại cảm xúc"
    if any(k in t for k in ["trải nghiệm", "dùng rồi", "cảm nhận", "review", "xài rồi"]):
        return "chia sẻ trải nghiệm"
    if any(k in t for k in ["câu chuyện", "giá trị", "thông điệp", "thương hiệu", "tinh thần"]):
        return "định hướng thương hiệu"
    return "hài hước / giải trí" if any(k in t for k in ["haha", "hihi", "vui", "cười"]) else "chia sẻ trải nghiệm"

def label_tactic(text):
    t = text.lower()
    if "?" in t:
        return "hỏi gợi mở"
    if any(k in t for k in ["ban đầu", "lúc đầu", "nhưng"]):
        return "chuyển ý tự nhiên"
    if any(emo in t for emo in ["😊","😁","😄","👍","🔥","✨","❤️","👌","🤝","🙌","🎉","!"]):
        return "cảm thán tích cực"
    if any(k in t for k in ["so với", "giống như", "kiểu như"]):
        return "so sánh nhẹ"
    if any(k in t for k in ["truyền cảm hứng", "động lực", "lan tỏa"]):
        return "truyền cảm hứng"
    if any(k in t for k in ["haha", "hihi", "😅", "😁"]):
        return "hài hước nhẹ"
    if any(k in t for k in ["mình thấy", "theo mình", "cá nhân", "trải nghiệm"]):
        return "đồng cảm cá nhân"
    if any(k in t for k in ["nên", "thử", "xem", "cân nhắc"]):
        return "đề xuất / khuyến nghị"
    return "đồng cảm cá nhân"

labeled = []
for i, c in enumerate(texts, 1):
    labeled.append({
        "id": i,
        "content": c,
        "muc_dich": label_purpose(c),
        "chien_thuat": label_tactic(c)
    })

# Naming from user-provided vars (assistant phải set trước khi chạy nếu người dùng đặt tên)
try:
    title = user_name_title
    stub  = user_name_stub
except NameError:
    title = "Seeding knowledge"; stub="seeding_knowledge"

# --------- Render & SAVE .md ---------
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

md_path = Path(f"/mnt/data/{stub}.md")
md_path.write_text("\n".join(md), encoding="utf-8")

# --------- SAVE flat JSON (summary, no nesting) ---------
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

# --------- SAVE Excel (thêm sheet LabeledComments) ---------
excel_path = Path(f"/mnt/data/{stub}.xlsx")
with pd.ExcelWriter(excel_path, engine="xlsxwriter") as writer:
    pd.DataFrame([flat]).to_excel(writer, index=False, sheet_name="Summary")
    df.to_excel(writer, index=False, sheet_name="ApprovedComments")
    pd.DataFrame({"tone_patterns": patterns}).to_excel(writer, index=False, sheet_name="Patterns")
    pd.DataFrame({"unigram": uni}).to_excel(writer, index=False, sheet_name="Keywords-Uni")
    pd.DataFrame({"bigram": [w for w,_ in bg]}).to_excel(writer, index=False, sheet_name="Keywords-Bi")
    pd.DataFrame({"trigram": [w for w,_ in tg]}).to_excel(writer, index=False, sheet_name="Keywords-Tri")
    pd.DataFrame(labeled).to_excel(writer, index=False, sheet_name="LabeledComments")

(md_path, json_path, excel_path)
```

---

### Ghi chú triển khai
- Hai cột mới (`muc_dich`, `chien_thuat`) đã được sinh tự động và xuất vào **sheet `LabeledComments`** của Excel.
- Bạn **không cần** tạo file schema riêng cho hai cột này, trừ khi team muốn chỉnh taxonomy thường xuyên. Nếu cần, tạo thêm một file `taxonomy_seeding.md` trong Knowledge ghi rõ danh mục và quy tắc gán — còn logic gán thì **giữ trong code** để bảo đảm nhất quán.
