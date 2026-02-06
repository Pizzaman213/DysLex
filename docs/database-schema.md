# Database Schema

## Entity Relationship Diagram

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│    users     │────<│   error_logs     │     │ error_patterns│
├──────────────┤     ├──────────────────┤     ├──────────────┤
│ id (PK)      │     │ id (PK)          │     │ id (PK)      │
│ email        │     │ user_id (FK)     │     │ name         │
│ name         │     │ original_text    │     │ description  │
│ password_hash│     │ corrected_text   │     │ category     │
│ created_at   │     │ error_type       │     │ examples     │
│ updated_at   │     │ context          │     └──────────────┘
└──────────────┘     │ confidence       │
       │             │ was_accepted     │
       │             │ created_at       │
       │             └──────────────────┘
       │
       ▼
┌──────────────────┐     ┌──────────────────┐
│  error_profiles  │     │ confusion_pairs  │
├──────────────────┤     ├──────────────────┤
│ id (PK)          │     │ id (PK)          │
│ user_id (FK)     │     │ language         │
│ overall_score    │     │ word1            │
│ patterns (JSONB) │     │ word2            │
│ confusion_pairs  │     │ category         │
│ achievements     │     │ frequency        │
│ updated_at       │     └──────────────────┘
└──────────────────┘
       │
       ▼
┌──────────────────┐
│  user_progress   │
├──────────────────┤
│ id (PK)          │
│ user_id (FK)     │
│ date             │
│ words_written    │
│ corrections_made │
│ accuracy_score   │
└──────────────────┘
```

## Tables

### users
Core user information and authentication.

### error_profiles
User's personalized error profile for adaptive learning.
- `patterns`: JSONB array of error patterns with mastery progress
- `confusion_pairs`: JSONB array of word pairs the user confuses
- `achievements`: JSONB array of earned achievements

### error_logs
Historical log of all detected errors and corrections.

### confusion_pairs
Language-specific confusion pair database (shared across users).

### error_patterns
Predefined dyslexia error pattern categories.

### user_progress
Daily progress tracking for analytics and achievements.
