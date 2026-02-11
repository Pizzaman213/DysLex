# Frustration Detection

## Purpose

Passively monitors writing behavior for signs of frustration and offers gentle check-in prompts. Never interrupts flow — only surfaces when frustration signals exceed a threshold.

## Detection Signals

`frontend/src/hooks/useFrustrationDetector.ts` monitors four signal types:

| Signal | Trigger | Weight |
|--------|---------|--------|
| **Rapid Deletion** | >20 chars deleted in 3 seconds | High |
| **Long Pause** | >30 seconds mid-sentence | Medium |
| **Short Bursts** | <5 words, 3+ times in a row | Medium |
| **Cursor Thrashing** | 5+ jumps >50 chars apart in 10 seconds | High |

## Scoring System

- Weighted frustration score with exponential decay (signals fade over time)
- Threshold: 0.6 on a 0-1 scale triggers check-in
- 10-minute cooldown between check-ins
- Cooldown interaction with AI Coach (checking in resets cooldown)

## Hook API

```typescript
const {
  shouldShowCheckIn,  // boolean — UI should show prompt
  checkInSignals,     // which signals triggered
  dismissCheckIn,     // user dismisses
  handleCheckInAction // user takes suggested action
} = useFrustrationDetector();
```

## Integration Points

- `sessionStore` — Records frustration signals for analytics
- AI Coach — Can be triggered from check-in action
- DraftMode — Primary consumer (monitors editor activity)

## Key Files

| File | Role |
|------|------|
| `frontend/src/hooks/useFrustrationDetector.ts` | Detection hook |

## Status

- [x] Four signal types implemented
- [x] Weighted scoring with exponential decay
- [x] Cooldown system
- [x] Session store integration
- [ ] Check-in UI component
- [ ] Coach integration from check-in
