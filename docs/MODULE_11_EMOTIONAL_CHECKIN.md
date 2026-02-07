# Module 11: Emotional Check-In System

## Overview

The Emotional Check-In System passively detects frustration through writing behavior patterns and offers gentle, empathetic support at the right moments. It extends DysLex AI's core philosophy of never interrupting creative flow.

**Status**: ✅ Implemented

## Key Features

### 1. Passive Frustration Detection

Four behavioral signals are monitored automatically:

| Signal | Detection Method | Threshold | What It Means |
|--------|-----------------|-----------|---------------|
| **Rapid Deletion** | Character deletions via TipTap transactions | >20 chars in 3 seconds | User repeatedly deleting and rewriting |
| **Long Pause** | Idle time between editor updates | >30 seconds mid-sentence | User stuck or uncertain |
| **Short Bursts** | Words added per typing session | <5 words, 3+ times in a row | Struggling to maintain flow |
| **Cursor Thrashing** | Selection position changes | 5+ jumps >50 chars in 10 seconds | Jumping around document, disoriented |

### 2. Weighted Scoring System

Each signal has a weight and severity:

```typescript
const SIGNAL_WEIGHTS = {
  rapid_deletion: 0.4,   // Strongest indicator
  long_pause: 0.2,
  short_burst: 0.3,
  cursor_thrash: 0.3,
};

// Signals decay exponentially over 2 minutes
// Check-in triggered when score >= 0.6
```

### 3. Empathetic Check-In Messages

Messages are:
- **Supportive**: "You're working hard on getting this right."
- **Non-judgmental**: "Taking your time is okay."
- **Actionable**: Offer specific next steps (voice mode, break, continue)

Example messages:

```
Primary: "Noticing a lot of backspacing. This part might feel tricky."
Suggestion: "Remember: first drafts don't need to be perfect."
Actions: [I'm Good]
```

```
Primary: "Stuck on what to say next?"
Suggestion: "Try speaking your thoughts out loud, or move to a different section."
Actions: [Switch to Voice] [Keep Thinking]
```

### 4. Smart Cooldown & Coordination

- **10-minute cooldown** between check-ins to avoid annoyance
- **2-minute spacing** between check-ins and AI Coach nudges
- **Session tracking** of all frustration events for analytics

## Architecture

```
┌─────────────────────────────────────────────┐
│ CheckInPrompt Component (UI)                │
│ - Banner at top of editor                  │
│ - Empathetic message + actions             │
└─────────────────────────────────────────────┘
                    ↑
┌─────────────────────────────────────────────┐
│ useFrustrationDetector Hook (Logic)        │
│ - 4 signal detection algorithms            │
│ - Weighted scoring system                  │
│ - Cooldown enforcement                     │
└─────────────────────────────────────────────┘
                    ↑
┌─────────────────────────────────────────────┐
│ sessionStore (State)                        │
│ - frustrationEvents[]                      │
│ - checkInHistory[]                         │
│ - lastCheckInTime                          │
└─────────────────────────────────────────────┘
```

## Implementation Files

### Core Files

| File | Purpose | Lines |
|------|---------|-------|
| `frontend/src/hooks/useFrustrationDetector.ts` | Detection algorithms and scoring | ~350 |
| `frontend/src/components/Editor/CheckInPrompt.tsx` | UI component | ~80 |
| `frontend/src/utils/checkInMessages.ts` | Message database | ~150 |
| `frontend/src/styles/check-in-prompt.css` | Component styling | ~120 |

### Modified Files

| File | Changes | Lines Added |
|------|---------|-------------|
| `frontend/src/stores/sessionStore.ts` | Frustration tracking state | +60 |
| `frontend/src/components/Editor/DyslexEditor.tsx` | Integration point | +15 |
| `frontend/src/hooks/useAICoach.ts` | Coordination logic | +10 |
| `frontend/src/styles/global.css` | Import CSS | +1 |

### Test Files

| File | Purpose | Lines |
|------|---------|-------|
| `frontend/src/hooks/__tests__/useFrustrationDetector.test.ts` | Unit tests | ~200 |

**Total**: ~970 lines of code across 8 files (5 new, 3 modified)

## How It Works

### 1. Signal Detection

Each signal runs independently:

**Rapid Deletion**:
```typescript
// Track deletions in 3-second rolling window
if (netChange < 0) {
  deletionWindow.push({ charCount, timestamp });
  if (totalDeleted >= 20) {
    recordFrustrationSignal({ type: 'rapid_deletion', severity: 0.8 });
  }
}
```

**Long Pause**:
```typescript
// Check every 5 seconds
const idleTime = Date.now() - lastActivityTime;
if (idleTime >= 30000 && isMidSentence) {
  recordFrustrationSignal({ type: 'long_pause', severity: 0.7 });
}
```

**Short Bursts**:
```typescript
// Track typing bursts, finalize on 2s pause
const recentBursts = burstHistory.slice(-3);
if (recentBursts.every(b => b.wordsAdded < 5)) {
  recordFrustrationSignal({ type: 'short_burst', severity: 0.8 });
}
```

**Cursor Thrashing**:
```typescript
// Count jumps >50 chars in 10-second window
if (jumpCount >= 5) {
  recordFrustrationSignal({ type: 'cursor_thrash', severity: 0.6 });
}
```

### 2. Scoring & Threshold

```typescript
function calculateFrustrationScore(signals: FrustrationSignal[]): number {
  return signals.reduce((score, signal) => {
    const age = now - signal.timestamp;
    const decayFactor = Math.exp(-age / 120000); // 2-min decay
    const weight = SIGNAL_WEIGHTS[signal.type];
    return score + (weight * signal.severity * decayFactor);
  }, 0);
}

// Trigger check-in if score >= 0.6 and cooldown passed
```

### 3. Message Selection

```typescript
// Single signal → specific message
if (signalTypes.length === 1) {
  const messages = MESSAGES[signalTypes[0]];
  return randomMessage(messages);
}

// Multiple signals → general support message
const messages = MESSAGES.mixed;
return randomMessage(messages);
```

### 4. User Actions

| Action ID | Behavior | Effect |
|-----------|----------|--------|
| `continue` | Dismiss check-in | Resume writing |
| `voice_mode` | Switch to voice input | Navigate to Capture Mode |
| `take_break` | Pause session | (Future: show timer/meditation) |

All actions are recorded in `sessionStore.checkInHistory` for analytics.

## Usage

### In Draft Mode (Automatic)

The system activates automatically when the editor is in draft mode:

```typescript
// DyslexEditor.tsx
const {
  shouldShowCheckIn,
  checkInSignals,
  dismissCheckIn,
  handleCheckInAction
} = useFrustrationDetector(mode === 'draft' ? editor : null);

return (
  <div className="dyslex-editor">
    {shouldShowCheckIn && (
      <CheckInPrompt
        signalTypes={checkInSignals}
        onDismiss={dismissCheckIn}
        onAction={handleCheckInAction}
      />
    )}
    <EditorContent editor={editor} />
  </div>
);
```

### Manual Testing

To trigger check-ins manually during development:

```typescript
// 1. Rapid Deletion Test
// Type 30 characters, then delete all within 2 seconds, repeat twice

// 2. Long Pause Test
// Type half a sentence, leave cursor mid-sentence, wait 35 seconds

// 3. Short Burst Test
// Type 3 words → pause 3s → type 4 words → pause 3s → type 2 words

// 4. Cursor Thrashing Test
// Jump cursor to end, start, middle, end, start within 8 seconds
```

## Configuration

### Thresholds (can be tuned)

```typescript
// Detection thresholds
const RAPID_DELETION_THRESHOLD = 20; // chars
const RAPID_DELETION_WINDOW = 3000; // ms
const LONG_PAUSE_THRESHOLD = 30000; // ms
const SHORT_BURST_THRESHOLD = 5; // words
const SHORT_BURST_COUNT = 3; // consecutive bursts
const CURSOR_JUMP_DISTANCE = 50; // chars
const CURSOR_JUMP_COUNT = 5; // jumps
const CURSOR_JUMP_WINDOW = 10000; // ms

// Scoring
const FRUSTRATION_THRESHOLD = 0.6; // 0-1 scale
const SIGNAL_DECAY_MS = 120000; // 2 minutes
const CHECK_IN_COOLDOWN = 600000; // 10 minutes
const INTERVENTION_SPACING = 120000; // 2 minutes
```

### Styling

Themes are supported via CSS custom properties:

```css
/* Cream Theme */
--bg-info: #E8F4F8;
--border-info: #B3D9E8;

/* Night Theme */
--bg-info: #2A2A35;
--border-info: #3A3A48;
```

## Accessibility

- **ARIA**: `role="status"` with `aria-live="polite"`
- **Keyboard**: Full keyboard navigation, Esc to dismiss
- **Screen Readers**: Messages announced politely
- **Reduced Motion**: Respects `prefers-reduced-motion`

## Analytics & Insights

All events are tracked in `sessionStore`:

```typescript
interface FrustrationEvent {
  type: 'rapid_deletion' | 'long_pause' | 'short_burst' | 'cursor_thrash';
  timestamp: number;
  severity: number;
  metadata?: Record<string, any>;
}

interface CheckInEvent {
  timestamp: number;
  signalTypes: string[];
  action: 'dismissed' | 'took_break' | 'voice_mode' | 'continued' | null;
}
```

Future dashboards can show:
- Most common frustration triggers
- Check-in effectiveness (action taken vs dismissed)
- Frustration patterns over time
- Correlation with corrections or word count

## Testing

### Unit Tests

```bash
cd frontend
npm test -- useFrustrationDetector.test.ts
```

Coverage includes:
- Hook initialization and cleanup
- Event listener registration
- Signal recording in sessionStore
- Dismissal and action handling
- Cooldown enforcement

### Manual Test Scenarios

| Scenario | Steps | Expected Result |
|----------|-------|----------------|
| Rapid Deletion | Type 30 chars, delete all, repeat twice | Check-in about backspacing |
| Long Pause | Type half sentence, wait 35s | Check-in about being stuck |
| Short Bursts | 3 words → pause → 4 words → pause → 2 words | Check-in about flow |
| Cursor Thrashing | Jump end→start→middle 5+ times in 8s | Check-in about jumping around |
| Cooldown | Trigger check-in, dismiss, trigger again immediately | No second check-in for 10 min |
| Coach Coordination | Trigger AI Coach nudge, then frustration signals within 2 min | No check-in (spacing enforced) |

## Future Enhancements

- **Adaptive Thresholds**: ML to personalize detection per user
- **Recovery Tracking**: Measure time to resume writing after check-in
- **Contextual Messages**: Reference specific section user is working on
- **Break Timer**: Built-in 2-minute meditation/breathing exercise
- **Progress Dashboard**: "Overcame X challenging moments" stat
- **A/B Testing**: Test message effectiveness, optimal thresholds

## Integration Points

### Works With

- ✅ **Draft Mode**: Primary activation context
- ✅ **AI Coach**: 2-minute spacing between interventions
- ✅ **Session Tracking**: All events logged for analytics
- ✅ **Theme System**: Supports Cream, Night, Blue-Tint

### Does Not Interfere With

- ✅ **Corrections**: Check-in is separate from correction flow
- ✅ **Voice Input**: Can trigger switch to voice mode
- ✅ **Snapshots**: Passive learning continues independently

## Philosophy Alignment

✅ **Never interrupts creative flow**: Banner-style, dismissible with one click

✅ **Respects the person**: Messages are supportive, never condescending

✅ **Show progress, not deficits**: "You're working hard" vs "You're struggling"

✅ **Actionable**: Every check-in offers clear next steps

✅ **Rare**: Maximum once per 10 minutes, only when truly needed

---

**Implementation Date**: 2026-02-06
**Module Status**: Complete and Tested
**Requires**: TipTap Editor, Zustand sessionStore, React 18+
