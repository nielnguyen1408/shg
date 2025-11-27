# ProMail Synthesizer | SHG — Knowledge Pack
Updated: 2025-10-14

This pack contains Markdown files you can upload to the **Knowledge** section of your custom GPT.

## What’s inside
- **01_Template_Chung.md** – The baseline enterprise email template.
- **02_Stylebook_Seed.md** – Initial stylebook rules (will be expanded as you feed approved emails).
- **03_Phrases_Preferred.md** – Recommended phrases/wording.
- **04_Phrases_Avoid.md** – Words/phrases to avoid.
- **05_Signature_Samples.md** – Signature block patterns.
- **06_Prompt_Format.md** – Input schema and usage pattern.
- **07_Rubric_Testcases.md** – Test cases & evaluation rubric.

## How to use
1) In ChatGPT, open **Create a GPT** → **Configure** → **Knowledge** → **Upload** these files.
2) Turn on **Code Interpreter & Data Analysis** capability.
3) In **Instructions**, paste the `System Prompt` from this pack (06).
4) Start a chat and provide inputs: **Mục đích** + **Thông tin/Nội dung** (bullets).
5) When ready, upload **approved** emails (redacted) to Knowledge and ask: “Cập nhật Stylebook từ các email [APPROVED]”.

## Notes
- Keep sensitive PII out, or redact before upload.
- Version your stylebook: `v1.0`, `v1.1`, … for safe rollback.
