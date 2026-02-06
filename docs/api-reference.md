# API Reference

Base URL: `http://localhost:8000/api`

## Corrections

### POST /corrections
Get text corrections using the two-tier LLM system.

**Request:**
```json
{
  "text": "Teh quick brown fox jumps over the lazzy dog.",
  "context": "Academic writing"
}
```

**Response:**
```json
{
  "corrections": [
    {
      "original": "Teh",
      "suggested": "The",
      "type": "transposition",
      "start": 0,
      "end": 3,
      "confidence": 0.98,
      "explanation": "Letters were swapped"
    }
  ]
}
```

### POST /corrections/quick
Quick correction using local model (no deep analysis).

## Profiles

### GET /profiles/me
Get the current user's error profile.

**Response:**
```json
{
  "user_id": "uuid",
  "overall_score": 65,
  "top_patterns": [
    {"id": "p1", "description": "b/d reversals", "mastered": false, "progress": 45}
  ],
  "confusion_pairs": [
    {"word1": "their", "word2": "there", "frequency": 12}
  ],
  "achievements": []
}
```

### PATCH /profiles/me
Update the current user's error profile.

### GET /profiles/me/patterns
Get the user's learned error patterns.

### GET /profiles/me/confusion-pairs
Get the user's common confusion pairs.

## Progress

### GET /progress
Get user's progress statistics.

**Response:**
```json
{
  "overall_score": 65,
  "words_written": 12500,
  "corrections_accepted": 342,
  "patterns_mastered": 8,
  "streak_days": 5,
  "achievements": []
}
```

### GET /progress/history
Get historical progress data.

### GET /progress/achievements
Get user's achievements.

## Users

### POST /users
Create a new user.

### GET /users/me
Get the current user's profile.

### PATCH /users/me
Update the current user's profile.

### DELETE /users/me
Delete the current user's account.

## Voice

### POST /voice/tts
Convert text to speech.

**Request:**
```json
{
  "text": "Hello, world!",
  "voice": "default"
}
```

**Response:**
```json
{
  "audio_url": "/audio/generated.mp3"
}
```

### POST /voice/stt
Convert speech to text. Upload audio file as multipart form data.

### GET /voice/voices
List available TTS voices.

## Health

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```
