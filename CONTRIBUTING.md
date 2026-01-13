# Contributing to Take My Dictation

## Development Setup

1. Fork and clone the repository
2. Run the setup script: `./setup.sh`
3. Create a `.env` file with your credentials
4. Activate virtual environment: `source venv/bin/activate`
5. Run tests: `pytest tests/ -v`

## Project Structure

```
take-my-dictation/
├── app/                      # Main application code
│   ├── api/                  # API endpoint handlers
│   │   ├── recordings.py     # Recording CRUD operations
│   │   ├── transcriptions.py # Transcription endpoints
│   │   ├── summaries.py      # Summary generation
│   │   └── admin.py          # Health & stats
│   ├── core/                 # Core configuration
│   │   └── config.py         # Settings management
│   ├── db/                   # Database setup
│   │   └── database.py       # SQLAlchemy async setup
│   ├── models/               # Database models
│   │   ├── recording.py      # Recording model
│   │   ├── transcription.py  # Transcription model
│   │   └── summary.py        # Summary model
│   ├── schemas/              # Pydantic validation
│   │   ├── recording.py      # Recording schemas
│   │   ├── transcription.py  # Transcription schemas
│   │   └── summary.py        # Summary schemas
│   ├── services/             # Business logic
│   │   ├── audio_service.py  # Audio file operations
│   │   ├── transcription_service.py  # Whisper integration
│   │   └── summary_service.py        # Claude integration
│   └── main.py               # FastAPI app initialization
├── tests/                    # Test suite
├── uploads/                  # Audio file storage
└── requirements.txt          # Python dependencies
```

## Code Style

### Python Style Guide

- Follow PEP 8
- Use type hints
- Write docstrings for all functions and classes
- Maximum line length: 100 characters

### Formatting

```bash
# Format code
black app/

# Lint code
ruff check app/

# Fix linting issues
ruff check app/ --fix
```

### Type Checking

```bash
# Run mypy (optional)
mypy app/
```

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api.py -v
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files with `test_` prefix
- Use descriptive test function names
- Use pytest fixtures for common setup

Example:
```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_upload_recording():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test implementation
        pass
```

## API Development

### Adding New Endpoints

1. Create/update router in `app/api/`
2. Define Pydantic schemas in `app/schemas/`
3. Add business logic to `app/services/`
4. Update database models if needed
5. Write tests
6. Update API documentation

### Database Migrations

Using Alembic (to be set up):

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Service Layer

### Audio Service

Handles file operations and audio processing:
- File upload and storage
- Duration extraction
- Format conversion

### Transcription Service

Integrates with OpenAI Whisper:
- Audio transcription
- Language detection
- Timestamp extraction

### Summary Service

Integrates with Anthropic Claude:
- Summary generation
- Key point extraction
- Action item identification
- Content categorization

## Adding New Features

### Example: Adding Translation Feature

1. **Create Model** (`app/models/translation.py`):
```python
from sqlalchemy import Column, String, ForeignKey
from app.db.database import Base

class Translation(Base):
    __tablename__ = "translations"
    id = Column(String, primary_key=True)
    transcription_id = Column(String, ForeignKey("transcriptions.id"))
    target_language = Column(String)
    translated_text = Column(Text)
```

2. **Create Schema** (`app/schemas/translation.py`):
```python
from pydantic import BaseModel

class TranslationCreate(BaseModel):
    transcription_id: str
    target_language: str

class TranslationResponse(BaseModel):
    id: str
    transcription_id: str
    target_language: str
    translated_text: str
```

3. **Create Service** (`app/services/translation_service.py`):
```python
class TranslationService:
    async def translate(self, text: str, target_lang: str):
        # Implementation
        pass
```

4. **Create API Router** (`app/api/translations.py`):
```python
from fastapi import APIRouter

router = APIRouter()

@router.post("/translate")
async def translate_text(...):
    # Implementation
    pass
```

5. **Register Router** (in `app/main.py`):
```python
from app.api import translations
app.include_router(translations.router, prefix="/translations", tags=["Translations"])
```

## Error Handling

Always use appropriate HTTP status codes:
- `200` - Success
- `201` - Created
- `204` - No Content (for deletes)
- `400` - Bad Request (validation errors)
- `404` - Not Found
- `500` - Internal Server Error

Example:
```python
from fastapi import HTTPException

if not recording:
    raise HTTPException(status_code=404, detail="Recording not found")
```

## Async Best Practices

- Use `async/await` for I/O operations
- Use `AsyncSession` for database operations
- Use async HTTP clients (httpx, aiohttp)
- Don't block the event loop

```python
# Good
async def process_file(file_path: str):
    async with aiofiles.open(file_path, 'rb') as f:
        data = await f.read()
    return data

# Bad
def process_file(file_path: str):
    with open(file_path, 'rb') as f:
        data = f.read()
    return data
```

## Environment Variables

Add new environment variables to:
1. `.env.example` - Template file
2. `app/core/config.py` - Settings class
3. `README.md` - Documentation

## Documentation

- Update README.md for user-facing features
- Update PROJECT_DOCUMENTATION.md for architecture
- Add docstrings to all public functions
- Include examples in API endpoints

## Pull Request Process

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Write code and tests
3. Run tests: `pytest tests/ -v`
4. Format code: `black app/`
5. Commit changes: `git commit -m "Add feature X"`
6. Push to GitHub: `git push origin feature/your-feature`
7. Create Pull Request

## Questions?

- Check PROJECT_DOCUMENTATION.md for architecture details
- Read the code - it's well documented!
- Review existing tests for examples
