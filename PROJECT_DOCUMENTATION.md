# Take My Dictation - Project Documentation

## Project Overview

**Take My Dictation** is a voice recording application with AI-powered summaries. Users can record audio notes, get intelligent transcriptions, and receive AI-generated summaries of their recordings.

## Core Features

### Phase 1: MVP (Minimum Viable Product)
1. **Audio Recording**
   - Record audio through the app
   - Upload pre-recorded audio files
   - Support common audio formats (MP3, WAV, M4A, OGG)

2. **Transcription**
   - Automatic speech-to-text conversion
   - High-accuracy transcription using AI
   - Support for multiple languages

3. **AI Summaries**
   - Generate intelligent summaries of transcriptions
   - Extract key points and action items
   - Categorize content automatically

4. **Storage & Retrieval**
   - Save recordings with metadata
   - List and search recordings
   - Retrieve transcriptions and summaries

### Phase 2: Enhanced Features
- User authentication and multi-user support
- Recording folders/categories
- Export functionality (PDF, TXT, DOCX)
- Audio playback with synchronized transcript
- Edit and refine transcriptions
- Custom summary templates
- Sharing capabilities

## Tech Stack

### Backend (FastAPI)
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with SQLAlchemy async ORM
- **Audio Processing**: FFmpeg for format conversion
- **Transcription**: OpenAI Whisper API or AssemblyAI
- **AI Summaries**: Anthropic Claude API
- **File Storage**: Local filesystem (Phase 1), S3-compatible storage (Phase 2)
- **Server**: Uvicorn (ASGI)

### Frontend (Future)
- React Native or Flutter for mobile app
- React for web interface

## API Architecture

### Endpoints Structure

#### Recordings
- `POST /recordings/upload` - Upload audio file
- `GET /recordings` - List all recordings
- `GET /recordings/{id}` - Get specific recording
- `DELETE /recordings/{id}` - Delete recording
- `GET /recordings/{id}/audio` - Stream audio file

#### Transcription
- `POST /transcriptions/create` - Create transcription from recording
- `GET /transcriptions/{recording_id}` - Get transcription
- `PUT /transcriptions/{id}` - Update transcription text

#### Summaries
- `POST /summaries/generate` - Generate AI summary
- `GET /summaries/{recording_id}` - Get summary
- `PUT /summaries/{id}/regenerate` - Regenerate summary

#### Admin
- `GET /admin/stats` - Usage statistics
- `GET /admin/health` - Health check

## Database Schema

### Recordings Table
```sql
- id (UUID, primary key)
- filename (string)
- original_filename (string)
- file_path (string)
- file_size (bigint)
- duration (float) - in seconds
- format (string) - audio format
- created_at (timestamp)
- updated_at (timestamp)
- status (enum: pending, processing, completed, failed)
```

### Transcriptions Table
```sql
- id (UUID, primary key)
- recording_id (UUID, foreign key)
- text (text)
- language (string)
- confidence (float)
- created_at (timestamp)
- updated_at (timestamp)
- provider (string) - whisper, assemblyai, etc.
```

### Summaries Table
```sql
- id (UUID, primary key)
- recording_id (UUID, foreign key)
- transcription_id (UUID, foreign key)
- summary_text (text)
- key_points (json)
- action_items (json)
- category (string)
- created_at (timestamp)
- model_used (string) - claude-3-opus, etc.
```

## File Structure

```
take-my-dictation/
├── app/
│   ├── api/
│   │   ├── recordings.py      # Recording endpoints
│   │   ├── transcriptions.py  # Transcription endpoints
│   │   ├── summaries.py       # Summary endpoints
│   │   └── admin.py           # Admin endpoints
│   ├── core/
│   │   ├── config.py          # Configuration & settings
│   │   └── security.py        # Security utilities (Phase 2)
│   ├── db/
│   │   ├── database.py        # Database connection
│   │   └── init_db.py         # Database initialization
│   ├── models/
│   │   ├── recording.py       # Recording SQLAlchemy model
│   │   ├── transcription.py   # Transcription model
│   │   └── summary.py         # Summary model
│   ├── schemas/
│   │   ├── recording.py       # Pydantic schemas for recordings
│   │   ├── transcription.py   # Pydantic schemas for transcriptions
│   │   └── summary.py         # Pydantic schemas for summaries
│   ├── services/
│   │   ├── audio_service.py   # Audio processing logic
│   │   ├── transcription_service.py  # Transcription API integration
│   │   ├── summary_service.py # AI summary generation
│   │   └── storage_service.py # File storage operations
│   └── main.py                # FastAPI application entry point
├── uploads/                   # Local audio file storage
├── tests/                     # Unit and integration tests
├── migrations/                # Alembic database migrations
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── .env                      # Environment variables (gitignored)
├── .gitignore                # Git ignore rules
├── README.md                 # Project README
├── docker-compose.yml        # Docker setup (Phase 2)
└── Dockerfile                # Docker configuration (Phase 2)
```

## Environment Variables

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost/take_my_dictation

# API Keys
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# File Storage
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE=104857600  # 100MB in bytes

# Audio Processing
ALLOWED_AUDIO_FORMATS=mp3,wav,m4a,ogg,flac
```

## Development Workflow

### Phase 1 Implementation Order
1. **Project Setup**
   - Initialize FastAPI project structure
   - Set up database with SQLAlchemy
   - Configure environment variables
   - Create base models and schemas

2. **Recording Management**
   - Implement file upload endpoint
   - Create recording storage service
   - Add recording list/retrieve endpoints
   - Test audio file handling

3. **Transcription Service**
   - Integrate Whisper API
   - Create transcription endpoints
   - Handle async transcription processing
   - Store transcription results

4. **AI Summary Service**
   - Integrate Claude API
   - Generate summaries from transcriptions
   - Extract key points and action items
   - Store summary results

5. **Testing & Documentation**
   - Write unit tests
   - Create API documentation
   - Test end-to-end workflows

## API Response Examples

### Upload Recording
```json
POST /recordings/upload
Response: {
  "id": "uuid-here",
  "filename": "recording_20240113_143022.mp3",
  "duration": 125.5,
  "status": "pending",
  "created_at": "2024-01-13T14:30:22Z"
}
```

### Get Transcription
```json
GET /transcriptions/{recording_id}
Response: {
  "id": "uuid-here",
  "recording_id": "uuid-here",
  "text": "Full transcription text here...",
  "language": "en",
  "confidence": 0.95,
  "created_at": "2024-01-13T14:31:00Z"
}
```

### Get Summary
```json
GET /summaries/{recording_id}
Response: {
  "id": "uuid-here",
  "recording_id": "uuid-here",
  "summary_text": "Brief summary of the recording...",
  "key_points": [
    "Important point 1",
    "Important point 2"
  ],
  "action_items": [
    "Follow up on task A",
    "Schedule meeting with B"
  ],
  "category": "meeting_notes",
  "created_at": "2024-01-13T14:32:00Z"
}
```

## Success Metrics

- Audio upload success rate > 99%
- Transcription accuracy > 90%
- Summary generation time < 10 seconds
- API response time < 500ms (excluding AI processing)
- Support files up to 100MB
- Handle concurrent uploads

## Future Enhancements

- Real-time transcription streaming
- Speaker diarization (identify different speakers)
- Custom vocabulary for domain-specific terms
- Multi-language support
- Voice commands for hands-free operation
- Integration with calendar apps
- Automated tagging and organization
- Collaboration features
- Mobile apps (iOS/Android)
- Browser extension for quick recording
