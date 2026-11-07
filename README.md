# پرسش و پاسخ از روی سند (RAG) — FastAPI + Streamlit

یه فایل PDF یا TXT آپلود می‌کنی، ازش سؤال می‌پرسی، و جواب رو همراه با بخش‌هایی از سند که برای جواب استفاده شده می‌گیری.

- منطق اصلی (خوندن فایل، تکه‌کردن، ذخیره، جست‌وجو، صدا زدن مدل زبانی) توی پوشه‌ی `rag/` هست و به هیچ‌کدوم از FastAPI یا Streamlit وابسته نیست.
- `api/` یه سرویس FastAPI با سه مسیر `POST /docs`، `POST /ask` و `GET /health` هست.
- `ui/` صفحه‌ی Streamlit هست که **فقط** به API درخواست HTTP می‌ده و مستقیم کد RAG رو صدا نمی‌زنه.

همه‌ی دستورها برای **Windows PowerShell** نوشته شدن و **Docker لازم نیست**.

---

## ۱. نصب (یک بار)

پیش‌نیاز: Python 3.10 یا جدیدتر.

```powershell
cd C:\Users\Mahanei\Desktop\MMD
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

> اگه می‌خوای venv رو activate کنی (`.\.venv\Scripts\Activate.ps1`) و PowerShell خطای Execution Policy داد، اول این رو بزن:
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
> بعد از activate به‌جای `.\.venv\Scripts\python.exe` می‌تونی فقط بنویسی `python`.

## ۲. تنظیم کلید API (از متغیر محیطی، نه داخل کد)

کلید هیچ‌جای کد نیست؛ از متغیر محیطی `OPENAI_API_KEY` خونده می‌شه. دو راه داری:

**راه الف — فایل `.env`** (پیشنهادی، این فایل توی `.gitignore` هست):

```powershell
copy .env.example .env
notepad .env
```

و توش بنویس:

```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...کلید خودت...
OPENAI_MODEL=gpt-4o-mini
```

**راه ب — فقط برای همین ترمینال:**

```powershell
$env:OPENAI_API_KEY = "sk-...کلید خودت..."
```

> اگه از سرویس سازگار با OpenAI دیگه‌ای (پروکسی، OpenRouter، سرور محلی و ...) استفاده می‌کنی، `OPENAI_BASE_URL` و `OPENAI_MODEL` رو هم تنظیم کن.

**مدل محلی (بدون VPN و بدون کلید، پیش‌فرض فعلی):** مدل Gemma 3 4B با برنامه‌ی `llama.cpp` روی خود کامپیوتر اجرا می‌شه. `run.bat` خودش اون رو روشن می‌کنه. فایل‌هاش توی پوشه‌ی `local_llm/` هستن:

```powershell
New-Item -ItemType Directory -Force local_llm
curl.exe -L -o local_llm\llama-cpu.zip https://github.com/ggml-org/llama.cpp/releases/download/b11711/llama-b11711-bin-win-cpu-x64.zip
Expand-Archive local_llm\llama-cpu.zip local_llm\bin
curl.exe -L -C - -o local_llm\gemma-3-4b-it-Q4_K_M.gguf https://huggingface.co/unsloth/gemma-3-4b-it-GGUF/resolve/main/gemma-3-4b-it-Q4_K_M.gguf
```

و توی `.env`:

```
OPENAI_API_KEY=local
OPENAI_BASE_URL=http://127.0.0.1:8080/v1
OPENAI_MODEL=gemma-3-4b (local)
LLM_TIMEOUT=600
```

روی CPU هر جواب حدود ۱ تا ۳ دقیقه طول می‌کشه. لاگ مدل توی `local_llm\server.log` هست.

**بدون کلید / بدون خرج اعتبار:** `LLM_PROVIDER=fake` بذار. در این حالت به‌جای مدل واقعی، مرتبط‌ترین بخش سند برگردونده می‌شه. برای امتحان کردن کل سیستم کافیه.

```powershell
$env:LLM_PROVIDER = "fake"
```

**OCR آفلاین (برای PDFهای اسکن‌شده یا با فونت قدیمی فارسی، مثل دفترچه‌های قلمچی):** یک بار این رو بزن (حدود ۵۵ مگ دانلود، بدون نیاز به ادمین):

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_ocr.ps1
```

Tesseract با زبان فارسی و انگلیسی توی `local_ocr/` نصب می‌شه. موقع آپلود، برنامه خودش صفحه‌هایی رو که متنشون خراب یا خالیه تشخیص می‌ده و فقط همون‌ها رو با OCR می‌خونه (یه PDF ۲۲ صفحه‌ای حدود ۴۰ ثانیه). اگه OCR نصب نباشه برنامه کار می‌کنه، فقط اون صفحه‌ها رد می‌شن و توی جواب آپلود (`unreadable_pages`) گزارش می‌شن.

## چه سؤال‌هایی می‌شه پرسید

| نمونه | چی کار می‌کنه |
|---|---|
| `رئیس‌جمهور حداقل چند سال باید سن داشته باشد؟` | جست‌وجو توی سند (حتی اگه زبان سؤال و سند فرق کنه) |
| `خلاصه‌ی این فایل رو بگو` / `این فایل چیه؟` | خلاصه از اول، وسط و آخر سند |
| `صفحه 4 چی میگه؟` | متن همون صفحه (شماره‌ی **چاپ‌شده** روی صفحه، اگه پیدا بشه) |
| `سوال 7 زیست` | مستقیم سؤال ۷ (چون توی بازه‌ی زیست‌شناسیه) |
| `سوال 33` | خودش می‌فهمه مال کدوم درسه (مثلاً فیزیک ۲۱–۴۰) |
| `سومین سوال فیزیک` یا `سوال 3 فیزیک` | سومین سؤالِ بازه‌ی فیزیک (مثلاً سؤال ۲۳) |
| `آخرین سوال زیست` | آخرین سؤال اون درس |
| `سوال 2 صفحه 8` | دومین سؤالِ صفحه‌ی ۸ |
| `سلام` | جواب فوری، بدون صدا زدن مدل |

برای سندهای سؤال‌دار (آزمون، جزوه‌ی تمرین)، موقع آپلود هر سؤال با شماره، درس و صفحه‌اش ذخیره می‌شه. درس‌ها از جدول اول دفترچه، تیترهای اول هر درس (مثل `فیزیک (2): ...`) یا در آخرین حالت از کلمات سؤال‌ها تشخیص داده می‌شن. چون OCR گاهی رقم دهگان رو جا می‌ندازه (`61-` رو `1-` می‌خونه)، شماره‌ها از ترتیب سؤال‌ها بازسازی می‌شن.

**پاسخنامه:** اگه پاسخنامه‌ی همون آزمون رو هم آپلود کنی و توی Streamlit از منوی «پاسخنامه (اختیاری)» انتخابش کنی (یا توی API `answer_key_doc_id` بفرستی)، برای «سوال 7 زیست» جواب از پاسخنامه خونده می‌شه. بدون پاسخنامه، متن سؤال نشون داده می‌شه و مدل محلی یه تحلیل کوتاه می‌ده که **ممکنه اشتباه باشه** (مدل کوچیک برای حل سؤال کنکور قابل اعتماد نیست).

## اجرای سریع

| دستور | چی رو روشن می‌کنه | آدرس |
|---|---|---|
| `.\run_api.bat` | فقط FastAPI (+ مدل محلی) | `http://127.0.0.1:8000/docs` |
| `.\run.bat` | FastAPI + Streamlit (+ مدل محلی) | `http://127.0.0.1:8000/docs` و `http://localhost:8501` |

API و Streamlit هر دو توی همین ترمینال اجرا می‌شن (اگه API از قبل روشن باشه، دوباره اجراش نمی‌کنه). برای خاموش کردن هر دو، `Ctrl+C` بزن.
اگه می‌خوای جدا جدا اجرا کنی، بخش ۳ و ۴ رو ببین (هر کدوم یه ترمینال جدا لازم داره).

## ۳. اجرای API

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.main:app --reload
```

API روی `http://127.0.0.1:8000` بالا میاد. چک کن:

```powershell
curl.exe http://127.0.0.1:8000/health
# {"status":"ok","llm":"openai/gpt-4o-mini"}   ← اگه "fake" بود یعنی مدل واقعی خاموشه
```

## ۴. اجرای Streamlit (اختیاری)

توی یه ترمینال **دیگه** (API باید روشن باشه):

```powershell
cd C:\Users\Mahanei\Desktop\MMD
.\.venv\Scripts\python.exe -m streamlit run ui/streamlit_app.py
```

مرورگر `http://localhost:8501` رو باز می‌کنه. فایل رو آپلود کن، روی **Process file** بزن، سؤال رو بنویس و **Ask** رو بزن. منابع جواب زیر بخش **Sources** هستن.
اگه سندی رو قبلاً از طریق API آپلود کردی، `doc_id`ش رو توی نوار کناری (Use an existing document) وارد کن.

---

## ۵. استفاده بدون Streamlit

### از طریق صفحه‌ی `/docs` (Swagger)

1. برو به `http://127.0.0.1:8000/docs`
2. **POST /docs** رو باز کن ← **Try it out** ← فایل رو انتخاب کن (مثلاً `evals\sample_doc.txt`) ← **Execute**
3. مقدار `doc_id` رو از جواب کپی کن.
4. **POST /ask** رو باز کن ← **Try it out** ← این رو بذار و **Execute** بزن:

```json
{
  "doc_id": "اینجا doc_id رو بذار",
  "question": "هر کارمند در سال چند روز مرخصی دارد؟"
}
```

> `GET /docs` صفحه‌ی Swagger هست و `POST /docs` آپلود فایل؛ هر دو روی یه آدرس‌ان و با هم تداخل ندارن.

### از طریق PowerShell (نمونه‌ی کامل با سند نمونه)

```powershell
[Console]::OutputEncoding = [Text.Encoding]::UTF8   # برای نمایش درست فارسی

# آپلود
$doc = curl.exe -s -X POST http://127.0.0.1:8000/docs -F "file=@evals/sample_doc.txt" | ConvertFrom-Json
$doc

# سؤال
$body = @{ doc_id = $doc.doc_id; question = "هر کارمند در سال چند روز مرخصی دارد؟" } | ConvertTo-Json
$res = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/ask `
        -ContentType "application/json; charset=utf-8" `
        -Body ([Text.Encoding]::UTF8.GetBytes($body))

$res.answer
$res.sources | Format-List chunk_index, page, score, text
```

نمونه‌ی جواب `POST /docs` (کد 201):

```json
{ "doc_id": "c45b1a1b7cf54404bd3fe3a0979065fe", "filename": "sample_doc.txt", "num_chunks": 3, "num_pages": null }
```

نمونه‌ی جواب `POST /ask` (کد 200؛ با مدل واقعی، مقدارها تقریبی‌ان):

```json
{
  "doc_id": "c45b1a1b7cf54404bd3fe3a0979065fe",
  "question": "هر کارمند در سال چند روز مرخصی دارد؟",
  "answer": "هر کارمند در سال ۲۶ روز مرخصی استحقاقی با حقوق دارد [1].",
  "sources": [
    { "chunk_index": 0, "page": null, "score": 1.82, "text": "... هر کارمند در سال ۲۶ روز مرخصی استحقاقی ..." }
  ]
}
```

- `sources` همون بخش‌هایی از سند هستن که به مدل داده شدن (به ترتیب ربط).
- `page` شماره‌ی صفحه توی فایل PDF و `printed_page` شماره‌ی چاپ‌شده روی خود صفحه‌ست (اگه پیدا بشه). برای TXT هر دو خالی‌ان.
- برای سندهای سؤال‌دار، `question` و `subject` هم پر می‌شن، و اگه منبعی از پاسخنامه باشه `answer_key: true` داره.
- جواب `POST /docs` هم `num_questions`، `sections` (درس‌ها و بازه‌ی شماره‌ها)، `ocr_pages` و `unreadable_pages` رو برمی‌گردونه.
- فیلد اختیاری `top_k` (۱ تا ۲۰) تعداد بخش‌هایی که بازیابی می‌شن رو تعیین می‌کنه.

---

## ۶. خطاها

| حالت | کد | نمونه‌ی `detail` |
|---|---|---|
| سؤال خالی یا فقط فاصله | 400 | `The question must not be empty.` |
| پسوند غیر از pdf/txt | 400 | `Unsupported file type '.png'...` |
| فایل خالی، PDF خراب/تقلبی، فایل باینری با پسوند txt، PDF بدون متن | 400 | `The file is not a valid PDF.` و ... |
| فایل بزرگ‌تر از `MAX_UPLOAD_MB` (پیش‌فرض ۱۰) | 413 | `File is larger than the 10 MB limit.` |
| `doc_id` ناموجود | 404 | `Document '...' was not found.` |
| کلید API تنظیم نشده | 503 | `OPENAI_API_KEY is not set...` |
| خطای سرویس مدل (کلید غلط، سهمیه، قطعی شبکه، تایم‌اوت، جواب خالی) | 502 | `Could not connect to the language model service.` و ... |

آپلود فایل حتی بدون کلید API هم کار می‌کنه، چون بازیابی محلیه. فقط `/ask` برای تولید جواب به مدل نیاز داره.

## ۷. تست‌ها (بدون خرج اعتبار API)

```powershell
.\.venv\Scripts\python.exe -m pytest
```

تست‌ها از یه مدل جعلی (و یه مدل عمداً خراب برای حالت خطا) استفاده می‌کنن و هیچ درخواستی به سرویس واقعی نمی‌فرستن. این‌ها رو پوشش می‌دن: سلامت سرویس، آپلود TXT و PDF، جواب همراه با منبع (شامل شماره‌ی صفحه‌ی PDF)، سند فارسی، سؤال خالی، فایل نامعتبر، سند ناموجود، فایل خیلی بزرگ، خطای مدل (502)، نبود کلید (503)، تبدیل خطاهای OpenAI، ماندگاری سند بعد از ری‌استارت، و کلاینت HTTP صفحه‌ی Streamlit.

## ۸. ارزیابی (eval) نمونه

`evals/` یه سند نمونه (`sample_doc.txt`) و چند سؤال با جواب مورد انتظار (`eval_set.json`) داره.

```powershell
# آفلاین با مدل جعلی، مجانی؛ فقط کیفیت بازیابی رو می‌سنجه
.\.venv\Scripts\python.exe -m evals.run_eval

# روی API در حال اجرا با مدل واقعی؛ کیفیت جواب رو هم می‌سنجه (اعتبار مصرف می‌کنه)
.\.venv\Scripts\python.exe -m evals.run_eval --api http://127.0.0.1:8000
```

- **retrieval hit:** حقیقت مورد انتظار توی بخش بازیابی‌شده هست یا نه (پیش‌فرض فقط بهترین بخش، `--top-k 1`).
- **answer hit:** حقیقت مورد انتظار توی جواب مدل اومده یا نه (فقط با مدل واقعی معنی داره).

نتیجه‌ی فعلی در حالت آفلاین: بازیابی ۸ از ۹. تنها مورد ناموفق سؤال انگلیسی روی سند فارسیه، چون مدل جعلی نمی‌تونه ترجمه کنه.

**سؤال به زبانی غیر از زبان سند:** جست‌وجو کلیدواژه‌ایه. برای همین اگه خط سؤال با خط سند فرق کنه (مثلاً سؤال فارسی روی PDF انگلیسی)، اول مدل زبانی سؤال رو به زبان سند ترجمه می‌کنه، بعد جست‌وجو انجام می‌شه. جواب همچنان به زبان سؤال برمی‌گرده. این کار یه درخواست اضافه به مدل لازم داره و فقط وقتی انجام می‌شه که زبان‌ها فرق کنن.

---

## ساختار پروژه

```
rag/            منطق اصلی، مستقل از وب
  loaders.py      خوندن PDF/TXT، تشخیص صفحه‌های خراب و فرستادنشون به OCR
  textnorm.py     یکسان‌سازی حروف و رقم‌های فارسی/عربی، تشخیص متن خراب (فونت قدیمی)
  ocr.py          OCR آفلاین با Tesseract (فارسی + انگلیسی)، چند صفحه هم‌زمان
  structure.py    تشخیص سؤال‌های شماره‌دار، جدول درس‌ها و شماره‌ی چاپی صفحه‌ها
  query.py        فهمیدن «سوال 7 زیست»، «سومین سوال فیزیک»، «صفحه 5» و پیدا کردن مستقیمشون
  chunking.py     تکه‌کردن متن با هم‌پوشانی
  store.py        ذخیره‌ی سندها به‌صورت JSON در data/ (بعد از ری‌استارت هم می‌مونن)
  retriever.py    جست‌وجوی BM25 محلی (بدون هزینه‌ی API، با پشتیبانی فارسی)
  llm.py          کلاینت OpenAI (و سازگارها) + مدل جعلی
  service.py      RAGService: ingest() و ask()
  config.py       تنظیمات از متغیرهای محیطی / .env
api/            FastAPI (main.py، schemas.py)
ui/             Streamlit (streamlit_app.py) + کلاینت HTTP (api_client.py)
tests/          تست‌های pytest
evals/          سند نمونه، سؤال‌ها و اسکریپت ارزیابی
```

## متغیرهای محیطی

| متغیر | پیش‌فرض | توضیح |
|---|---|---|
| `LLM_PROVIDER` | `openai` | `openai` یا `fake` |
| `OPENAI_API_KEY` | — | کلید مدل (برای `openai` لازمه) |
| `OPENAI_MODEL` | `gpt-4o-mini` | نام مدل |
| `OPENAI_BASE_URL` | — | برای سرویس‌های سازگار با OpenAI |
| `LLM_TIMEOUT` | `60` | ثانیه |
| `LLM_REASONING_EFFORT` | — | برای مدل‌های «فکرکننده» مثل DeepSeek V4: `low` / `medium` / `high` |
| `RAG_DATA_DIR` | `data` | محل ذخیره‌ی سندها |
| `MAX_UPLOAD_MB` | `10` | حداکثر حجم فایل |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `800` / `150` | اندازه‌ی تکه‌ها (کاراکتر) |
| `TOP_K` | `4` | تعداد پیش‌فرض بخش‌های بازیابی‌شده |
| `RAG_API_URL` | `http://127.0.0.1:8000` | آدرس API برای Streamlit |
| `OCR_TESSERACT` | — | مسیر `tesseract.exe` اگه جای دیگه‌ای نصبه (پیش‌فرض `local_ocr\tesseract`) |
| `OCR_LANGUAGES` | `fas+eng` | زبان‌های OCR |
| `OCR_DPI` | `300` | وضوح تصویر صفحه برای OCR |
#   a o i - s t r e a m 
 
 #   f a s t - s t r e a m l i t  
 