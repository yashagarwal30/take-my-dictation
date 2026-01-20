# Take My Dictation - Claude Code Context

## Project Overview

Take My Dictation is an AI-powered voice recording application with automatic transcription and intelligent summaries. Users can record or upload audio, which is transcribed using OpenAI Whisper, and summarized using Claude AI.

**Key Features:**
- Audio recording and upload (MP3, WAV, M4A, OGG, FLAC)
- Automatic transcription using OpenAI Whisper
- AI-generated summaries with key points and action items
- User authentication and trial system
- Subscription management via Razorpay
- Usage tracking and analytics
- Export functionality (PDF, DOCX, TXT)
- Background job processing for monthly resets

## Tech Stack

### Backend
- **Framework**: FastAPI with async/await
- **Database**: PostgreSQL with SQLAlchemy ORM (async)
- **Authentication**: JWT tokens with passlib/bcrypt
- **AI Services**:
  - OpenAI Whisper API for transcription
  - Anthropic Claude for summaries
- **Audio Processing**: FFmpeg, pydub
- **Payments**: Razorpay integration
- **Background Jobs**: APScheduler
- **Email**: SendGrid

### Frontend
- **Framework**: React with TypeScript
- **Styling**: Tailwind CSS
- **Routing**: React Router
- **HTTP Client**: Axios

## Project Structure

```
take-my-dictation/
├── app/
│   ├── api/                      # API route handlers
│   │   ├── auth.py              # Authentication endpoints (register, login, verify)
│   │   ├── users.py             # User management
│   │   ├── recordings.py        # Recording upload/list/delete
│   │   ├── transcriptions.py    # Transcription creation/retrieval
│   │   ├── summaries.py         # Summary generation
│   │   ├── payments.py          # Razorpay payment integration
│   │   ├── trials.py            # Trial management
│   │   ├── analytics.py         # Analytics endpoints
│   │   └── admin.py             # Admin endpoints
│   ├── core/
│   │   ├── config.py            # Settings and configuration
│   │   ├── security.py          # JWT, password hashing
│   │   ├── dependencies.py      # FastAPI dependencies
│   │   └── trial_limits.py      # Trial usage limits
│   ├── db/
│   │   └── database.py          # Database connection and session
│   ├── models/                  # SQLAlchemy models
│   │   ├── user.py              # User, Subscription models
│   │   ├── recording.py         # Recording model
│   │   ├── transcription.py     # Transcription model
│   │   ├── summary.py           # Summary model
│   │   └── email_verification.py
│   ├── schemas/                 # Pydantic schemas for validation
│   │   ├── user.py
│   │   ├── recording.py
│   │   ├── transcription.py
│   │   └── summary.py
│   ├── services/                # Business logic
│   │   ├── audio_service.py                 # Audio metadata extraction
│   │   ├── audio_processor.py               # Audio processing
│   │   ├── audio_enhancer.py                # Audio enhancement
│   │   ├── audio_retention_service.py       # Audio file retention policies
│   │   ├── transcription_service.py         # Transcription orchestration
│   │   ├── whisper_transcriber.py           # Whisper API wrapper
│   │   ├── production_whisper_service.py    # Production Whisper service
│   │   ├── summary_service.py               # Summary orchestration
│   │   ├── summarization_service.py         # Claude API wrapper
│   │   ├── export_service.py                # PDF/DOCX export
│   │   ├── email_service.py                 # SendGrid email
│   │   ├── usage_tracking_service.py        # Usage tracking
│   │   ├── analytics_service.py             # Analytics
│   │   └── scheduler.py                     # Background jobs
│   └── main.py                  # FastAPI app initialization
├── migrations/                  # Alembic database migrations
├── frontend/                    # React frontend
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── pages/              # Page components
│   │   ├── services/           # API client
│   │   └── App.tsx             # Main app component
│   └── package.json
├── uploads/                     # Audio file storage
├── tests/                       # Test files
├── requirements.txt             # Python dependencies
├── .env                        # Environment variables (not in git)
├── .env.example                # Environment template
└── README.md                   # Project documentation
```

## Key Concepts

### User Management
- Users register with email/password
- Email verification required via SendGrid
- JWT-based authentication
- Trial users start with limited usage
- Subscription tiers: TRIAL, BASIC, PREMIUM

### Audio Processing Flow
1. **Upload**: User uploads audio file via `/recordings/upload`
2. **Storage**: File stored in `uploads/` directory
3. **Metadata**: FFmpeg extracts duration and format
4. **Transcription**: Created via `/transcriptions/create`
   - Audio sent to OpenAI Whisper API
   - Text stored in database
5. **Summary**: Generated via `/summaries/generate`
   - Transcription sent to Claude API
   - Summary with key points and action items returned

### Subscription System
- **Trial**: Limited transcriptions per month
- **Basic**: More transcriptions, basic features
- **Premium**: Unlimited transcriptions, all features
- Razorpay integration for payments
- Monthly usage reset via background job

### Usage Tracking
- Tracks transcriptions, summaries, exports per user
- Monthly limits enforced based on subscription tier
- Background job resets usage on 1st of each month

### Audio Retention
- Trial users: 7 days audio retention
- Paid users: Configurable retention
- Background job cleans up old audio files
- Transcriptions/summaries kept indefinitely

## Important Files to Know

### Configuration
- [app/core/config.py](app/core/config.py) - All settings, environment variables
- [.env.example](.env.example) - Required environment variables template

### Database
- [app/db/database.py](app/db/database.py) - Database connection setup
- [migrations/](migrations/) - Alembic migrations for schema changes

### Authentication
- [app/api/auth.py](app/api/auth.py) - Registration, login, email verification
- [app/core/security.py](app/core/security.py) - JWT token creation, password hashing

### Core Features
- [app/api/recordings.py](app/api/recordings.py) - Audio upload/management
- [app/api/transcriptions.py](app/api/transcriptions.py) - Transcription endpoints
- [app/api/summaries.py](app/api/summaries.py) - Summary generation
- [app/services/transcription_service.py](app/services/transcription_service.py) - Transcription logic
- [app/services/summary_service.py](app/services/summary_service.py) - Summary logic

### Payments
- [app/api/payments.py](app/api/payments.py) - Razorpay integration, webhook handling

### Background Jobs
- [app/services/scheduler.py](app/services/scheduler.py) - APScheduler setup, monthly reset job

## Common Development Tasks

### Adding a New API Endpoint
1. Define Pydantic schemas in `app/schemas/`
2. Add route handler in appropriate `app/api/` file
3. Implement business logic in `app/services/`
4. Update database models if needed in `app/models/`
5. Create migration if schema changed: `alembic revision --autogenerate -m "description"`

### Running the Application
```bash
# Backend
source venv/bin/activate
python -m uvicorn app.main:app --reload

# Frontend
cd frontend && npm start

# Both (recommended)
./start-all.sh
```

### Database Migrations
```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Testing
```bash
# Run tests
pytest tests/ -v

# Run specific test
pytest tests/test_auth.py -v
```

## Environment Variables

Required variables in `.env`:

```env
# API
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/take_my_dictation

# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Authentication
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Email (SendGrid)
SENDGRID_API_KEY=SG...
SENDGRID_FROM_EMAIL=noreply@example.com

# Razorpay
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...

# Frontend
FRONTEND_URL=http://localhost:3000

# Storage
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE=104857600  # 100MB
ALLOWED_AUDIO_FORMATS=mp3,wav,m4a,ogg,flac
```

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Key Business Logic

### Trial Limits
- Defined in [app/core/trial_limits.py](app/core/trial_limits.py)
- Enforced via dependency injection
- Usage tracked in [app/services/usage_tracking_service.py](app/services/usage_tracking_service.py)

### Audio Retention Policy
- Trial users: 7 days
- Paid users: Configurable (default 30 days for Basic, unlimited for Premium)
- Implemented in [app/services/audio_retention_service.py](app/services/audio_retention_service.py)
- Scheduled job runs daily to clean up expired files

### Monthly Usage Reset
- Scheduled for 1st of every month at 00:00 UTC
- Resets usage counters for all users
- Implemented in [app/services/scheduler.py](app/services/scheduler.py)

## Development Guidelines

### Code Style
- Use `black` for formatting: `black app/`
- Use `ruff` for linting: `ruff check app/`
- Type hints encouraged but not strictly enforced

### Database Queries
- Use async SQLAlchemy throughout
- Always use dependency injection for database sessions
- Close sessions properly (handled by FastAPI dependencies)

### Error Handling
- Use FastAPI's `HTTPException` for API errors
- Log errors appropriately
- Return meaningful error messages to frontend

### Security
- Never commit `.env` file
- Always hash passwords before storing
- Validate all user inputs with Pydantic schemas
- Use parameterized queries (SQLAlchemy ORM handles this)
- Verify JWT tokens on protected endpoints

## Common Debugging Tips

### Database Connection Issues
- Ensure PostgreSQL is running: `brew services list`
- Check `DATABASE_URL` format: `postgresql+asyncpg://user:pass@host/db`
- Verify database exists: `psql -l`

### API Key Errors
- Check `.env` file has all required keys
- Verify keys are valid (not expired/revoked)
- Check API usage limits on provider dashboards

### Audio Processing Errors
- Ensure FFmpeg is installed: `ffmpeg -version`
- Check file format is supported
- Verify file size is within limits

### Background Job Issues
- Check scheduler is started in [app/main.py](app/main.py:31)
- View logs for job execution
- Verify timezone settings for scheduled jobs

## Recent Changes

Based on git history:
- **2026-01-19**: Migrated from Stripe to Razorpay for payments
- **2026-01-15**: Added comprehensive subscription enforcement and UI improvements
- **2026-01-15**: Implemented user management, trial system, and background jobs
- **2026-01-14**: Documentation consolidation and frontend additions

## Additional Documentation

- [README.md](README.md) - Setup and usage guide
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - Detailed API endpoint documentation
- [PRODUCT_SPECIFICATIONS.md](PRODUCT_SPECIFICATIONS.md) - Product requirements
- [USER_GUIDE.md](USER_GUIDE.md) - End-user documentation
- [SECURITY.md](SECURITY.md) - Security considerations
- [QUICKSTART.md](QUICKSTART.md) - Quick start guide

## Frontend Architecture

The React frontend is located in [frontend/](frontend/) directory:
- Built with Create React App
- TypeScript for type safety
- Tailwind CSS for styling
- Axios for API communication
- React Router for navigation

Key frontend files:
- [frontend/src/App.tsx](frontend/src/App.tsx) - Main application component
- [frontend/src/services/api.ts](frontend/src/services/api.ts) - API client
- [frontend/src/components/](frontend/src/components/) - Reusable components
- [frontend/src/pages/](frontend/src/pages/) - Page components

## Notes for Claude Code

When making changes:
1. **Always read files first** before modifying them
2. **Check related files** - changes to models often require schema updates
3. **Consider migrations** - database changes need Alembic migrations
4. **Update tests** if adding new features
5. **Check environment variables** if adding new config
6. **Frontend/backend coordination** - API changes may require frontend updates
7. **Subscription limits** - new features may need trial limit enforcement
8. **Background jobs** - consider if new features need scheduled tasks

Common patterns:
- Dependency injection used extensively via FastAPI's `Depends()`
- Async/await for all database operations
- Pydantic for request/response validation
- HTTPException for error responses
- JWT bearer token authentication on protected routes
