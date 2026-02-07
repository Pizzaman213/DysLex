# Polish Mode — Review & Refine

## Purpose

Polish Mode is the final stage where users review and refine their writing. It uses Tier 2 deep analysis (Nemotron) for structural suggestions, readability scoring, and comprehensive corrections with tracked changes.

**Key insight**: Editing is different from writing. Polish Mode is for when users are ready to focus on quality, not idea generation.

## User Experience

1. User clicks "Polish" when draft feels complete
2. Full-document analysis runs (1-5 seconds)
3. Tracked changes view shows all suggestions
4. Readability score and stats appear
5. User accepts/dismisses changes as desired
6. Session summary shows accomplishments

### What Users See
- Tracked changes (additions in green, removals in strikethrough)
- Readability score (friendly framing)
- Word count and writing stats
- "Read Aloud" button
- Accept/Dismiss controls for each change
- Session summary at end

### What Users Don't See
- Nemotron processing
- Deep analysis algorithms
- Complexity of suggestions

## Technical Implementation

### Polish Mode Component

```typescript
// frontend/src/components/WritingModes/PolishMode.tsx
export function PolishMode() {
  const { content, corrections } = useEditorStore();
  const { speak, stop, isSpeaking } = useTextToSpeech();
  const [showStats, setShowStats] = useState(false);

  const wordCount = content.split(/\s+/).filter(Boolean).length;
  const correctionCount = corrections.length;

  return (
    <div className="polish-mode">
      <div className="polish-controls">
        <button onClick={() => isSpeaking ? stop() : speak(content)}>
          {isSpeaking ? 'Stop' : 'Read Aloud'}
        </button>
        <button onClick={() => setShowStats(!showStats)}>
          {showStats ? 'Hide Stats' : 'Show Stats'}
        </button>
      </div>

      {showStats && <WritingStats wordCount={wordCount} />}

      <Editor mode="polish" />
    </div>
  );
}
```

### Deep Analysis Request

```python
# backend/app/core/llm_orchestrator.py
async def deep_analysis(text: str, user_id: str, context: str = None):
    """Tier 2 analysis using Nemotron."""
    # Load user's Error Profile
    profile = await get_user_profile(user_id)

    # Build personalized prompt
    prompt = build_deep_analysis_prompt(text, profile)

    # Call Nemotron for comprehensive review
    # Returns: corrections, structural suggestions, style feedback
```

### Readability Scoring

```typescript
// Friendly readability metrics (not academic)
interface ReadabilityScore {
  level: 'Easy to Read' | 'Clear' | 'Moderate' | 'Complex';
  details: {
    avgSentenceLength: number;
    avgWordLength: number;
    passiveVoicePercent: number;
  };
}
```

## Key Files

### Frontend
- `frontend/src/components/WritingModes/PolishMode.tsx` — Main component
- `frontend/src/hooks/useTextToSpeech.ts` — MagpieTTS integration
- (Future) `frontend/src/components/Polish/TrackedChanges.tsx`
- (Future) `frontend/src/components/Polish/SessionSummary.tsx`

### Backend
- `backend/app/services/nemotron_client.py` — Deep analysis
- `backend/app/services/tts_service.py` — MagpieTTS read-back

## Tracked Changes UI

```
┌───────────────────────────────────────────────┐
│ The quick brown ~~fxo~~ → fox jumps over      │
│ the lazy dog. ~~Its~~ → It's a beautiful day. │
│                                               │
│ [✓ Accept] [✗ Dismiss]                        │
└───────────────────────────────────────────────┘
```

- Additions shown in green
- Removals in strikethrough
- One-click accept/dismiss
- "Accept All" option

## Read Aloud (MagpieTTS)

```typescript
// frontend/src/hooks/useTextToSpeech.ts
export function useTextToSpeech() {
  const speak = useCallback((text: string) => {
    // Call MagpieTTS via backend
    // Stream audio to browser
    // Highlight current word/sentence
  }, []);
}
```

Features:
- Natural human-sounding voice
- Adjustable speed
- Word highlighting as it reads
- Pause/resume/stop controls

## Session Summary

When user finishes Polish Mode:

```
┌─────────────────────────────────────┐
│ Great session!                       │
│                                      │
│ 📝 750 words written                 │
│ ✨ 12 improvements made              │
│ 🎯 3 new words mastered              │
│ 🔥 Writing streak: 5 days            │
│                                      │
│ [Save & Exit]  [Continue Writing]    │
└─────────────────────────────────────┘
```

Always positive framing. Never shows "errors made."

## Accessibility Requirements

- **Read aloud**: Core accessibility feature
- **Keyboard navigation**: Accept/dismiss via keyboard
- **High contrast**: Changes visible in all themes
- **Screen reader**: Changes announced clearly
- **No time pressure**: User controls pace

## Integration Points

- **Draft Mode**: Receives completed draft
- **Error Profile**: Deep analysis updates profile
- **Progress Dashboard**: Session data logged
- **Export**: Final document ready for export

## NVIDIA NIM Integration

### Nemotron Deep Analysis
```python
# Full document analysis
# Structural suggestions
# Style improvements
# Context-aware corrections
```

### MagpieTTS Read-Back
```python
# Natural TTS
# Multiple voice options
# Adjustable speed
# Streaming audio
```

## Status

- [x] Basic component structure
- [x] TTS hook implemented
- [x] Stats display
- [ ] Tracked changes UI
- [ ] Deep analysis integration
- [ ] Session summary
- [ ] MagpieTTS integration
