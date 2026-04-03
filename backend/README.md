# Call Center Compliance API

AI-powered call center compliance analysis API. Accepts Base64-encoded MP3 recordings and performs multi-stage AI analysis to return structured compliance metrics.

## Description

This API processes call center recordings (Hinglish/Tanglish) through a multi-stage AI pipeline:

1. **Speech-to-Text** — OpenAI Whisper transcribes the MP3 audio with language-specific hints
2. **Summarization** — GPT-4o-mini generates a concise call summary
3. **SOP Validation** — LLM-powered detection of Greeting → ID → Problem → Solution → Closing
4. **Analytics** — Classifies payment intent, rejection reason, and customer sentiment
5. **Keyword Extraction** — Extracts domain-relevant keywords from the transcript

## Tech Stack

- **Framework:** FastAPI + Uvicorn
- **Task Queue:** Celery + Redis (async heavy AI processing)
- **STT:** OpenAI Whisper (`large-v3`) — handles Hinglish & Tanglish
- **LLM:** OpenAI GPT-4o-mini — summarization, SOP analysis, analytics, keywords
- **Validation:** Pydantic v2
- **Logging:** structlog

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/call-center-compliance.git
cd call-center-compliance/backend
```

### 2. Install Dependencies

```bash
# Recommended: use a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

# FFmpeg is required for Whisper audio processing
# Ubuntu/Debian:
sudo apt install ffmpeg

# macOS:
brew install ffmpeg
```

### 3. Set Environment Variables

```bash
cp .env.example .env
# Edit .env with your actual keys
```

Required values in `.env`:
```env
API_KEY=sk_track3_987654321
OPENAI_API_KEY=sk-your-openai-key
REDIS_URL=redis://localhost:6379/0
```

### 4. Start Redis

```bash
# Using Docker (recommended):
docker run -d -p 6379:6379 redis:alpine

# Or install locally and start:
redis-server
```

### 5. Start the Celery Worker

```bash
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2
```

### 6. Run the Application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API will be live at: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

## API Usage

### Endpoint

```
POST /api/v1/call-analytics
```

### Headers

```
Content-Type: application/json
x-api-key: sk_track3_987654321
```

### Request Body

```json
{
  "language": "Tamil",
  "audioFormat": "mp3",
  "audioBase64": "<base64-encoded-mp3>"
}
```

### cURL Example

```bash
curl -X POST http://localhost:8000/api/v1/call-analytics \
  -H "Content-Type: application/json" \
  -H "x-api-key: sk_track3_987654321" \
  -d '{
    "language": "Tamil",
    "audioFormat": "mp3",
    "audioBase64": "SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU2LjM2..."
  }'
```

### Sample Response

```json
{
  "status": "success",
  "language": "Tamil",
  "transcript": "Agent: Vanakkam...",
  "summary": "Agent discussed outstanding EMI of ₹5000...",
  "sop_validation": {
    "greeting": true,
    "identification": false,
    "problemStatement": true,
    "solutionOffering": true,
    "closing": true,
    "complianceScore": 0.8,
    "adherenceStatus": "NOT_FOLLOWED",
    "explanation": "Agent did not confirm customer identity."
  },
  "analytics": {
    "paymentPreference": "EMI",
    "rejectionReason": "NONE",
    "sentiment": "Positive"
  },
  "keywords": ["EMI", "outstanding payment", "Guvi Institution"]
}
```

## Approach

### SOP Validation Logic
The SOP validator uses GPT-4o-mini with a strict system prompt defining each of the 5 stages. The compliance score is computed as `true_count / 5`. All 5 stages must be present for `FOLLOWED` status.

### Payment & Rejection Classification
The analytics engine uses zero-temperature LLM inference with `response_format: json_object` to ensure strict enum output. Values are then validated against Python enums before being returned.

### Why Celery + Redis?
Whisper transcription can take 15–60 seconds on CPU. Using Celery prevents HTTP timeout errors and allows horizontal scaling by adding more workers.

## Running Tests

```bash
pytest tests/ -v
```

## Project Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI app + lifespan
│   ├── core/
│   │   ├── config.py             # Settings (pydantic-settings)
│   │   ├── security.py           # API key auth
│   │   └── logging.py            # structlog setup
│   ├── api/v1/
│   │   └── routes.py             # POST /call-analytics
│   ├── schemas/
│   │   ├── request.py            # Input validation
│   │   └── response.py           # Output schema
│   ├── services/
│   │   ├── stt_service.py        # Whisper STT
│   │   ├── summarizer.py         # LLM summarization
│   │   ├── sop_validator.py      # SOP compliance detection
│   │   ├── analytics_engine.py   # Payment + rejection + sentiment
│   │   ├── keyword_extractor.py  # Keyword extraction
│   │   └── pipeline.py           # Orchestration
│   ├── workers/
│   │   ├── celery_app.py         # Celery configuration
│   │   └── tasks.py              # Async task definitions
│   └── utils/
│       ├── enums.py              # Strict classification enums
│       └── helpers.py            # Base64 decode, cleanup, timing
├── tests/
│   └── test_api.py               # Full test suite
├── requirements.txt
├── .env.example
└── README.md
```
