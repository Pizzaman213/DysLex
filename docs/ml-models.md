# ML Models

## Overview

DysLex AI uses a multi-model approach for intelligent corrections:

1. **Quick Correction Model** - Local ONNX model for fast, common corrections
2. **Error Classifier** - Categorizes errors by type
3. **Deep Analysis** - Nemotron via NVIDIA NIM for complex cases

## Quick Correction Model

### Purpose
Handle common spelling errors and simple grammar issues locally in the browser.

### Architecture
- Input: Text string
- Output: Array of corrections with positions and types
- Format: ONNX for browser inference via ONNX Runtime Web

### Training Data
- Synthetic dyslexic errors generated from correct text
- Public datasets of common misspellings
- Anonymized user correction data (with consent)

### Personalization
Per-user adapter layers can be trained to handle individual error patterns.

## Error Classifier

### Purpose
Categorize detected errors for targeted learning.

### Categories
- **Reversal**: b/d, p/q letter confusion
- **Transposition**: Adjacent letter swaps (teh → the)
- **Phonetic**: Sound-based spelling (becuase → because)
- **Omission**: Missing letters (writting → writing)
- **Addition**: Extra letters (untill → until)
- **Confusion**: Homophone/similar word mix-ups

## Deep Analysis (Nemotron)

### Purpose
Handle complex grammar, context-dependent corrections, and nuanced word choice.

### When Used
- Long or complex sentences
- No quick corrections found
- User requests deep analysis

### Personalization
Prompts are dynamically constructed using the user's error profile.

## Confusion Pairs Database

Language-specific databases of commonly confused words:
- English: their/there/they're, your/you're, etc.
- Spanish: a/ha, hay/ahí/ay, etc.
- French: a/à, ou/où, etc.
