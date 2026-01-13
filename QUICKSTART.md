# Quick Start Guide - Take My Dictation

Get up and running in 5 minutes!

## Prerequisites Checklist

- [ ] Python 3.11 or higher installed
- [ ] PostgreSQL installed and running
- [ ] FFmpeg installed
- [ ] OpenAI API key (get at https://platform.openai.com/api-keys)
- [ ] Anthropic API key (get at https://console.anthropic.com/)

## Installation Steps

### 1. Run Setup Script

```bash
cd /Users/yashvardhanagarwal/Documents/take-my-dictation
chmod +x setup.sh
./setup.sh
```

### 2. Create Database

```bash
# Using createdb command
createdb take_my_dictation

# OR using psql
psql -U postgres
CREATE DATABASE take_my_dictation;
\q
```

### 3. Configure Environment

Edit the `.env` file and add your API keys:

```bash
nano .env
```

Update these values:
- `DATABASE_URL` - Your PostgreSQL connection string
- `OPENAI_API_KEY` - Your OpenAI API key
- `ANTHROPIC_API_KEY` - Your Anthropic API key

### 4. Start the Server

```bash
# Activate virtual environment
source venv/bin/activate

# Run the server
python run.py
```

The API will start at `http://localhost:8000`

## Test the API

### 1. Check Health

```bash
curl http://localhost:8000/admin/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "Take My Dictation API",
  "version": "1.0.0"
}
```

### 2. View API Documentation

Open in your browser:
- http://localhost:8000/docs (Interactive Swagger UI)

### 3. Upload a Test Recording

```bash
# Upload an audio file
curl -X POST "http://localhost:8000/recordings/upload" \
  -F "file=@/path/to/your/audio.mp3"
```

### 4. Create Transcription

```bash
# Replace RECORDING_ID with the ID from step 3
curl -X POST "http://localhost:8000/transcriptions/create" \
  -H "Content-Type: application/json" \
  -d '{"recording_id": "RECORDING_ID"}'
```

### 5. Generate Summary

```bash
# Replace RECORDING_ID with your recording ID
curl -X POST "http://localhost:8000/summaries/generate" \
  -H "Content-Type: application/json" \
  -d '{"recording_id": "RECORDING_ID"}'
```

## Complete Example Workflow

```bash
# 1. Upload audio
RESPONSE=$(curl -s -X POST "http://localhost:8000/recordings/upload" \
  -F "file=@meeting.mp3")

# Extract recording ID
RECORDING_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "Recording ID: $RECORDING_ID"

# 2. Transcribe
curl -X POST "http://localhost:8000/transcriptions/create" \
  -H "Content-Type: application/json" \
  -d "{\"recording_id\": \"$RECORDING_ID\"}"

# 3. Generate summary
curl -X POST "http://localhost:8000/summaries/generate" \
  -H "Content-Type: application/json" \
  -d "{\"recording_id\": \"$RECORDING_ID\"}"

# 4. Get the summary
curl "http://localhost:8000/summaries/$RECORDING_ID" | python3 -m json.tool
```

## Troubleshooting

### FFmpeg Not Found

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg
```

### PostgreSQL Not Running

```bash
# macOS
brew services start postgresql

# Ubuntu
sudo service postgresql start
```

### Database Connection Failed

Check your `DATABASE_URL` in `.env`:
```env
DATABASE_URL=postgresql+asyncpg://USERNAME:PASSWORD@localhost/take_my_dictation
```

Replace `USERNAME` and `PASSWORD` with your PostgreSQL credentials.

### Port Already in Use

Change the port in `.env`:
```env
API_PORT=8001
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) for architecture details
- Explore the interactive API docs at http://localhost:8000/docs
- Review the code in the `app/` directory

## Getting API Keys

### OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Sign up or log in
3. Click "Create new secret key"
4. Copy the key to your `.env` file

### Anthropic API Key
1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Navigate to API Keys
4. Create a new key
5. Copy the key to your `.env` file

## Support

For issues or questions:
- Check the [README.md](README.md) troubleshooting section
- Review the [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md)
- Test endpoints using the interactive docs at `/docs`
