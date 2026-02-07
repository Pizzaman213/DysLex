# Error Profile System

## Purpose

The Error Profile is the "adaptive brain" of DysLex AI. It's a per-user database that tracks individual dyslexic error patterns, enabling personalized corrections that improve over time.

**Key insight**: Every person with dyslexia makes different mistakes. Generic spell checkers treat everyone the same. DysLex AI learns YOUR specific patterns.

## User Experience

Users never interact with the Error Profile directly. They just write, and over time:
- Corrections become more accurate
- Their specific error patterns are caught faster
- The system stops flagging words they use intentionally
- Progress dashboard shows improvement

## What Gets Tracked

### Error Frequency Map
Tracks how often each specific error occurs:
```json
{
  "becuase": {"correct": "because", "count": 47, "last_seen": "2024-01-15"},
  "teh": {"correct": "the", "count": 112, "last_seen": "2024-01-15"},
  "definately": {"correct": "definitely", "count": 23, "last_seen": "2024-01-14"}
}
```

### Error Type Classification
Breakdown by dyslexic error category:
```json
{
  "reversal": 0.34,      // b/d, p/q swaps
  "phonetic": 0.28,      // spelling by sound
  "homophone": 0.22,     // their/there/they're
  "omission": 0.10,      // missing letters
  "transposition": 0.06  // letter order swaps
}
```

### Confusion Pairs
Words the user frequently mixes up:
```json
[
  {"word1": "their", "word2": "there", "frequency": 12},
  {"word1": "effect", "word2": "affect", "frequency": 8},
  {"word1": "your", "word2": "you're", "frequency": 15}
]
```

### Improvement Tracking
Historical data showing progress:
```json
{
  "teh": {"week_1": 15, "week_2": 12, "week_3": 8, "week_4": 3},
  "becuase": {"week_1": 10, "week_2": 10, "week_3": 7, "week_4": 5}
}
```

### Context Patterns
Behavioral patterns:
- Errors increase in documents > 500 words
- Fewer errors in familiar topics
- More errors late in writing sessions
- Specific error spikes in academic vs casual writing

## Technical Implementation

### Database Schema

```sql
-- Per-user error profile
CREATE TABLE error_profiles (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    overall_score INTEGER DEFAULT 50,
    patterns JSONB DEFAULT '[]',
    confusion_pairs JSONB DEFAULT '[]',
    achievements JSONB DEFAULT '[]',
    updated_at TIMESTAMP
);

-- Individual error logs
CREATE TABLE error_logs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    original_text TEXT NOT NULL,
    corrected_text TEXT NOT NULL,
    error_type VARCHAR(50),
    context TEXT,
    confidence FLOAT,
    was_accepted BOOLEAN,
    created_at TIMESTAMP
);
```

### Profile Service

```python
# backend/app/core/error_profile.py

async def get_user_profile(user_id: str, db: AsyncSession) -> ErrorProfile:
    """Get or create a user's error profile."""
    # Returns structured profile data

async def update_user_profile(user_id: str, update: ErrorProfileUpdate, db: AsyncSession):
    """Update profile with new error data."""
    # Merges new patterns with existing

async def record_correction(user_id: str, original: str, corrected: str, error_type: str, db: AsyncSession):
    """Record a single correction for learning."""
    # Updates frequency maps, confusion pairs, etc.
```

### Integration with LLM

The Error Profile is injected into LLM prompts:

```python
# backend/app/core/prompt_builder.py

def build_correction_prompt(text: str, user_patterns: list, confusion_pairs: list):
    return f"""
    USER ERROR PROFILE:
    - Most common errors: {user_patterns[:20]}
    - Confusion pairs: {confusion_pairs}

    Prioritize checking for these patterns in the text.
    """
```

## Key Files

### Backend
- `backend/app/core/error_profile.py` — Main profile logic
- `backend/app/db/models.py` — SQLAlchemy models
- `backend/app/db/repositories/error_pattern_repo.py` — Database access
- `backend/app/api/routes/profiles.py` — API endpoints

### Database
- `database/schema/init.sql` — Table definitions
- `database/seeds/error_types.sql` — Predefined error categories
- `database/seeds/confusion_pairs_en.sql` — Common English homophones

### ML
- `ml/error_classification/error_types.json` — Error category definitions
- `ml/confusion_pairs/en.json` — English confusion pairs

## API Endpoints

```
GET  /api/profiles/me              — Get current user's profile
PATCH /api/profiles/me             — Update profile
GET  /api/profiles/me/patterns     — Get learned patterns
GET  /api/profiles/me/confusion-pairs — Get confusion pairs
```

## Integration Points

- **Adaptive Loop**: Feeds corrections into profile
- **Quick Correction Model**: Uses profile for personalization
- **Deep Analysis LLM**: Receives profile in prompt
- **Progress Dashboard**: Reads improvement metrics

## Privacy Considerations

- All profile data is per-user and private
- Data never shared between users
- User can export/delete their profile
- No profile data sent to third parties

## Status

- [x] Database schema designed
- [x] Backend models implemented
- [x] API endpoints implemented
- [ ] Full adaptive loop integration
- [ ] Profile export/delete functionality
- [ ] Admin analytics (anonymized)
