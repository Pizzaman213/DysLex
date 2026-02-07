# Progress Dashboard

## Purpose

The Progress Dashboard shows users their improvement over time. It's designed to motivate and encourage — never to shame or highlight deficits. Users discover their progress when they choose to look.

**Core principle**: Show progress, not problems. Celebrate growth.

## User Experience

### What Users See
- Overall "Writing Strength" score (positive framing)
- Patterns mastered (words they've internalized)
- Recent achievements (gamification without pressure)
- Writing streak (encourages consistency)
- Trend charts (showing improvement over time)

### What Users Never See
- "Errors made" counts
- "Mistakes" or "failures"
- Comparisons to other users
- Any negative framing

## Dashboard Sections

### 1. Writing Strength Meter

```
┌─────────────────────────────────────┐
│ Your Writing Strength               │
│                                     │
│ ████████████░░░░░░░░ 65%           │
│                                     │
│ "Strong and growing!"               │
└─────────────────────────────────────┘
```

Labels by score:
- 0-20: "Getting Started"
- 21-40: "Learning"
- 41-60: "Growing"
- 61-80: "Strong"
- 81-100: "Excellent"

### 2. Patterns Mastered

```
┌─────────────────────────────────────┐
│ Patterns You've Learned             │
│                                     │
│ ✓ their/there/they're    Mastered!  │
│ ● double letters         78%        │
│ ● b/d reversals          45%        │
│                                     │
│ 3 patterns in progress              │
└─────────────────────────────────────┘
```

A "mastered" pattern is one where errors have dropped to near-zero for 2+ weeks.

### 3. Achievements

```
┌─────────────────────────────────────┐
│ Recent Achievements                 │
│                                     │
│ 🎯 First Steps     Started writing  │
│ 🔥 5-Day Streak    Keep it up!      │
│ ⭐ Word Master     10 words learned │
└─────────────────────────────────────┘
```

Achievements are:
- Earned through writing, not explicit actions
- Always positive and encouraging
- Designed to build habits

### 4. Writing Stats

```
┌─────────────────────────────────────┐
│ This Week                           │
│                                     │
│ 📝 2,450 words written              │
│ ✨ 15 improvements made             │
│ 🎯 4 new words mastered             │
│ 📈 12% improvement this month       │
└─────────────────────────────────────┘
```

## Technical Implementation

### Frontend Component

```typescript
// frontend/src/components/Panels/ProgressDashboard.tsx
export function ProgressDashboard() {
  const { profile, isLoading } = useErrorProfile();

  if (isLoading) return <Loading />;
  if (!profile) return <EmptyState />;

  return (
    <div className="progress-dashboard">
      <StrengthMeter score={profile.overallScore} />
      <PatternsList patterns={profile.topPatterns} />
      <AchievementsList achievements={profile.achievements} />
      <WeeklyStats stats={profile.weeklyStats} />
    </div>
  );
}
```

### Strength Label Logic

```typescript
function getStrengthLabel(score: number): string {
  if (score >= 80) return 'Excellent';
  if (score >= 60) return 'Strong';
  if (score >= 40) return 'Growing';
  if (score >= 20) return 'Learning';
  return 'Getting Started';
}
```

### Achievement Types

```typescript
interface Achievement {
  id: string;
  name: string;
  description: string;
  icon: string;
  earnedAt: string;
  category: 'streak' | 'milestone' | 'mastery';
}

const achievementDefinitions = [
  { id: 'first-steps', name: 'First Steps', icon: '🎯', trigger: 'first_session' },
  { id: 'streak-3', name: '3-Day Streak', icon: '🔥', trigger: 'streak_3' },
  { id: 'streak-7', name: 'Week Warrior', icon: '🔥', trigger: 'streak_7' },
  { id: 'words-100', name: 'Centurion', icon: '📝', trigger: 'words_100' },
  { id: 'words-1000', name: 'Prolific', icon: '📚', trigger: 'words_1000' },
  { id: 'master-5', name: 'Pattern Pro', icon: '⭐', trigger: 'patterns_5' },
];
```

## Backend API

```python
# backend/app/api/routes/progress.py

@router.get("", response_model=ProgressStats)
async def get_progress(user_id: CurrentUserId, db: DbSession):
    """Get user's progress statistics."""
    return ProgressStats(
        overall_score=65,
        words_written=12500,
        corrections_accepted=342,
        patterns_mastered=8,
        streak_days=5,
        achievements=[...],
    )

@router.get("/history")
async def get_progress_history(user_id: CurrentUserId, days: int = 30):
    """Get historical progress for charts."""
    return {"history": [...], "period_days": days}
```

## Data Model

```python
# Stored in error_profiles table (JSONB)
{
    "overall_score": 65,
    "patterns": [
        {"id": "p1", "description": "their/there", "mastered": true, "progress": 100},
        {"id": "p2", "description": "double letters", "mastered": false, "progress": 78}
    ],
    "achievements": [
        {"id": "first-steps", "earned_at": "2024-01-01"}
    ],
    "weekly_stats": [
        {"week": "2024-W01", "words": 2450, "improvements": 15}
    ]
}
```

## Key Files

### Frontend
- `frontend/src/components/Panels/ProgressDashboard.tsx`
- `frontend/src/hooks/useErrorProfile.ts`

### Backend
- `backend/app/api/routes/progress.py`
- `backend/app/models/progress.py`

## Accessibility

- **Color coding**: Always paired with icons/text
- **Screen reader**: Progress announced meaningfully
- **No pressure**: Dashboard is opt-in to view
- **Positive language**: All text is encouraging

## Privacy

- Progress is private to each user
- No leaderboards or comparisons
- Data can be exported/deleted
- Never shared with third parties

## Status

- [x] Component structure designed
- [x] Strength meter implemented
- [x] Patterns list implemented
- [ ] Achievements system
- [ ] Historical charts
- [ ] Weekly stats calculation
- [ ] Backend endpoints complete
