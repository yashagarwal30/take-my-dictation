# Take My Dictation

AI-powered voice recording app with automatic transcription and intelligent summaries. Record audio, get accurate transcriptions, and receive AI-generated summaries with key points and action items.

## Features

- **Audio Upload**: Support for MP3, WAV, M4A, OGG, and FLAC formats
- **Automatic Transcription**: High-accuracy speech-to-text using OpenAI Whisper
- **AI Summaries**: Intelligent summaries with key points and action items using Claude
- **RESTful API**: Well-documented FastAPI endpoints
- **Async Operations**: Fast, non-blocking database and API operations
- **PostgreSQL Database**: Production-ready data storage

## Tech Stack

### Backend
- **FastAPI**: Modern Python web framework
- **PostgreSQL**: Database with async SQLAlchemy ORM
- **OpenAI Whisper**: Speech-to-text transcription
- **Anthropic Claude**: AI-powered summary generation
- **FFmpeg**: Audio processing and metadata extraction

### Frontend
- **React**: UI framework
- **Tailwind CSS**: Styling
- **React Router**: Navigation
- **Axios**: HTTP client

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL
- FFmpeg (`brew install ffmpeg` on macOS)

### 1. Clone and Setup

```bash
cd /Users/yashvardhanagarwal/Documents/take-my-dictation

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Setup

```bash
# Create PostgreSQL database
createdb take_my_dictation

# Or using psql
psql -U postgres
CREATE DATABASE take_my_dictation;
\q
```

### 3. Environment Configuration

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

# Database
DATABASE_URL=postgresql+asyncpg://username:password@localhost/take_my_dictation

# API Keys
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# File Storage
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE=104857600

# Audio Processing
ALLOWED_AUDIO_FORMATS=mp3,wav,m4a,ogg,flac
```

### 4. Run the Application

**Option 1: Use Startup Scripts (Recommended)**

Start both backend and frontend with a single command:

```bash
./start-all.sh
```

This will:
- Start the backend on http://localhost:8000
- Start the frontend on http://localhost:3000
- Open your browser automatically
- Monitor both services
- Handle port conflicts and errors

To stop, press `Ctrl+C`

**Option 2: Start Services Separately**

Backend only:
```bash
./start-backend.sh
```

Frontend only:
```bash
cd frontend
npm start
```

Backend (manual):
```bash
source venv/bin/activate
python -m uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`
The frontend will be available at `http://localhost:3000`

## API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Recordings

**Upload Recording**
```bash
curl -X POST "http://localhost:8000/recordings/upload" \
  -F "file=@recording.mp3"
```

**List Recordings**
```bash
curl "http://localhost:8000/recordings/?page=1&page_size=10"
```

**Get Recording**
```bash
curl "http://localhost:8000/recordings/{recording_id}"
```

**Download Audio**
```bash
curl "http://localhost:8000/recordings/{recording_id}/audio" --output audio.mp3
```

**Delete Recording**
```bash
curl -X DELETE "http://localhost:8000/recordings/{recording_id}"
```

### Transcriptions

**Create Transcription**
```bash
curl -X POST "http://localhost:8000/transcriptions/create" \
  -H "Content-Type: application/json" \
  -d '{"recording_id": "your-recording-id"}'
```

**Get Transcription**
```bash
curl "http://localhost:8000/transcriptions/{recording_id}"
```

**Update Transcription**
```bash
curl -X PUT "http://localhost:8000/transcriptions/{transcription_id}" \
  -H "Content-Type: application/json" \
  -d '{"text": "Corrected transcription text"}'
```

### Summaries

**Generate Summary**
```bash
curl -X POST "http://localhost:8000/summaries/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "recording_id": "your-recording-id",
    "custom_prompt": "Focus on action items"
  }'
```

**Get Summary**
```bash
curl "http://localhost:8000/summaries/{recording_id}"
```

**Regenerate Summary**
```bash
curl -X PUT "http://localhost:8000/summaries/{summary_id}/regenerate?custom_prompt=Be more concise"
```

### Admin

**Health Check**
```bash
curl "http://localhost:8000/admin/health"
```

**Usage Statistics**
```bash
curl "http://localhost:8000/admin/stats"
```

## Example Workflow

```bash
# 1. Upload an audio file
RESPONSE=$(curl -X POST "http://localhost:8000/recordings/upload" \
  -F "file=@my_meeting.mp3")

RECORDING_ID=$(echo $RESPONSE | jq -r '.id')
echo "Recording ID: $RECORDING_ID"

# 2. Create transcription
curl -X POST "http://localhost:8000/transcriptions/create" \
  -H "Content-Type: application/json" \
  -d "{\"recording_id\": \"$RECORDING_ID\"}"

# 3. Generate summary
curl -X POST "http://localhost:8000/summaries/generate" \
  -H "Content-Type: application/json" \
  -d "{\"recording_id\": \"$RECORDING_ID\"}"

# 4. Get the summary
curl "http://localhost:8000/summaries/$RECORDING_ID" | jq
```

## Project Structure

```
take-my-dictation/
├── app/
│   ├── api/                  # API route handlers
│   │   ├── recordings.py     # Recording endpoints
│   │   ├── transcriptions.py # Transcription endpoints
│   │   ├── summaries.py      # Summary endpoints
│   │   └── admin.py          # Admin endpoints
│   ├── core/
│   │   └── config.py         # Configuration
│   ├── db/
│   │   └── database.py       # Database setup
│   ├── models/               # SQLAlchemy models
│   │   ├── recording.py
│   │   ├── transcription.py
│   │   └── summary.py
│   ├── schemas/              # Pydantic schemas
│   │   ├── recording.py
│   │   ├── transcription.py
│   │   └── summary.py
│   ├── services/             # Business logic
│   │   ├── audio_service.py
│   │   ├── transcription_service.py
│   │   └── summary_service.py
│   └── main.py               # FastAPI app
├── uploads/                  # Audio file storage
├── tests/                    # Tests
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Formatting

```bash
black app/
ruff check app/
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_HOST` | Server host | `0.0.0.0` |
| `API_PORT` | Server port | `8000` |
| `DEBUG` | Debug mode | `True` |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `OPENAI_API_KEY` | OpenAI API key for Whisper | Required |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude | Required |
| `UPLOAD_DIR` | Audio file storage directory | `./uploads` |
| `MAX_UPLOAD_SIZE` | Max file size in bytes | `104857600` (100MB) |
| `ALLOWED_AUDIO_FORMATS` | Allowed audio formats | `mp3,wav,m4a,ogg,flac` |

## Troubleshooting

### FFmpeg Not Found

Install FFmpeg:
- **macOS**: `brew install ffmpeg`
- **Ubuntu**: `sudo apt-get install ffmpeg`
- **Windows**: Download from https://ffmpeg.org/

### Database Connection Error

Make sure PostgreSQL is running:
```bash
# macOS
brew services start postgresql

# Ubuntu
sudo service postgresql start
```

Check your `DATABASE_URL` in `.env` file.

### API Key Errors

Verify your API keys are correctly set in `.env`:
- Get OpenAI API key: https://platform.openai.com/api-keys
- Get Anthropic API key: https://console.anthropic.com/

## Future Enhancements

- [ ] User authentication and multi-user support
- [ ] Real-time transcription streaming
- [ ] Speaker diarization (identify different speakers)
- [ ] Export to PDF, DOCX, TXT
- [ ] Mobile apps (iOS/Android)
- [ ] Web frontend
- [ ] Docker containerization
- [ ] Cloud storage integration (S3)
- [ ] Webhook notifications
- [ ] Batch processing

## Frontend

The React frontend is located in the `frontend/` directory. It provides:
- Audio recording interface
- Real-time transcription processing
- AI summary display with multiple formats
- Recording dashboard
- Subscription/pricing page

See [frontend/README.md](frontend/README.md) for frontend-specific documentation.

## Startup Scripts

Three convenience scripts are provided:
- `start-all.sh` - Start both backend and frontend
- `start-backend.sh` - Start backend only
- `start-frontend.sh` - Start frontend only

These scripts handle:
- Dependency checking
- Port conflict resolution
- Automatic logging
- Graceful shutdown

## Support

For issues and questions, check the troubleshooting section above or review the API documentation at http://localhost:8000/docs
