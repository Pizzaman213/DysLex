"""
Generate synthetic dyslexic error dataset for training BERT token classifier.

Creates realistic dyslexic spelling errors including:
- Letter reversals (b/d, p/q, n/u)
- Letter omissions
- Letter repetitions
- Phonetic substitutions
- Common dyslexic patterns
"""

import json
import random
from pathlib import Path
from typing import List, Tuple

# Common clean sentences from various domains
BASE_SENTENCES = [
    "I went to the store yesterday.",
    "The quick brown fox jumps over the lazy dog.",
    "She is reading a book in the library.",
    "We need to finish this project by Friday.",
    "The weather today is very nice.",
    "He plays basketball every weekend.",
    "They are planning a trip to Europe.",
    "The meeting starts at three o'clock.",
    "I love listening to music while working.",
    "Can you help me with this problem?",
    "The teacher explained the lesson clearly.",
    "We should arrive at the airport early.",
    "She writes in her journal every night.",
    "The movie was very interesting and exciting.",
    "I need to buy groceries after work.",
    "He enjoys cooking Italian food.",
    "They live in a small town near the mountains.",
    "The concert was absolutely amazing.",
    "I usually wake up at seven in the morning.",
    "She graduated from university last year.",
]

# Error patterns with replacement rules
ERROR_PATTERNS = {
    # Letter reversals
    'reversal': [
        ('b', 'd'), ('d', 'b'),
        ('p', 'q'), ('q', 'p'),
        ('n', 'u'), ('u', 'n'),
        ('m', 'w'), ('w', 'm'),
    ],

    # Common dyslexic misspellings (whole word)
    'common': {
        'the': ['teh', 'hte', 'th'],
        'because': ['becuase', 'becasue', 'becase', 'becuse'],
        'receive': ['recieve', 'recive', 'receeve'],
        'their': ['thier', 'ther', 'thair'],
        'said': ['sed', 'siad', 'sayd'],
        'was': ['wuz', 'wus', 'wa'],
        'when': ['wen', 'whe', 'whne'],
        'what': ['wat', 'wht', 'wath'],
        'with': ['whit', 'wit', 'wih'],
        'from': ['form', 'fro', 'frm'],
        'have': ['hav', 'ahve', 'haev'],
        'there': ['ther', 'thre', 'thier'],
        'would': ['wuld', 'woud', 'wolud'],
        'could': ['culd', 'coud', 'colud'],
        'people': ['poeple', 'peopl', 'peple'],
        'important': ['importent', 'importnt', 'improtant'],
        'different': ['diffrent', 'diferent', 'differant'],
        'thought': ['thoght', 'thught', 'thout'],
        'through': ['thru', 'throgh', 'thrugh'],
        'should': ['shoud', 'shuld', 'shld'],
        'about': ['abut', 'abot', 'abou'],
    },

    # Letter omissions (drop middle letters)
    'omission': {
        'friend': 'frend',
        'often': 'oftn',
        'listen': 'lisen',
        'castle': 'casle',
        'night': 'nigt',
        'right': 'rigt',
        'light': 'ligt',
        'might': 'migt',
    },

    # Phonetic substitutions
    'phonetic': {
        'enough': 'enuf',
        'laugh': 'laf',
        'tough': 'tuf',
        'phone': 'fone',
        'photo': 'foto',
        'elephant': 'elefant',
        'fantastic': 'fantastik',
    },
}


def inject_reversal_error(word: str) -> Tuple[str, bool]:
    """Inject a letter reversal error into a word."""
    for old_char, new_char in ERROR_PATTERNS['reversal']:
        if old_char in word:
            idx = word.index(old_char)
            corrupted = word[:idx] + new_char + word[idx+1:]
            return corrupted, True
    return word, False


def inject_common_error(word: str) -> Tuple[str, bool]:
    """Replace word with common dyslexic misspelling."""
    word_lower = word.lower()
    if word_lower in ERROR_PATTERNS['common']:
        errors = ERROR_PATTERNS['common'][word_lower]
        corrupted = random.choice(errors)
        # Preserve capitalization
        if word[0].isupper():
            corrupted = corrupted.capitalize()
        return corrupted, True
    return word, False


def inject_omission_error(word: str) -> Tuple[str, bool]:
    """Omit a middle letter from the word."""
    if len(word) <= 3:
        return word, False

    word_lower = word.lower()
    if word_lower in ERROR_PATTERNS['omission']:
        corrupted = ERROR_PATTERNS['omission'][word_lower]
        if word[0].isupper():
            corrupted = corrupted.capitalize()
        return corrupted, True

    # Random omission for words > 5 chars
    if len(word) > 5 and random.random() < 0.3:
        idx = random.randint(1, len(word) - 2)
        corrupted = word[:idx] + word[idx+1:]
        return corrupted, True

    return word, False


def inject_phonetic_error(word: str) -> Tuple[str, bool]:
    """Replace with phonetic spelling."""
    word_lower = word.lower()
    if word_lower in ERROR_PATTERNS['phonetic']:
        corrupted = ERROR_PATTERNS['phonetic'][word_lower]
        if word[0].isupper():
            corrupted = corrupted.capitalize()
        return corrupted, True
    return word, False


def corrupt_sentence(sentence: str) -> Tuple[str, List[int]]:
    """
    Inject 1-3 errors into a sentence.

    Returns:
        corrupted_text: Text with errors
        error_positions: List of word indices that have errors (0-indexed)
    """
    words = sentence.split()
    num_errors = random.randint(1, min(3, len(words)))
    error_indices = random.sample(range(len(words)), num_errors)

    error_positions = []

    for idx in error_indices:
        word = words[idx]

        # Try different error types
        error_funcs = [
            inject_common_error,
            inject_reversal_error,
            inject_omission_error,
            inject_phonetic_error,
        ]
        random.shuffle(error_funcs)

        for error_func in error_funcs:
            corrupted, success = error_func(word)
            if success:
                words[idx] = corrupted
                error_positions.append(idx)
                break

    return ' '.join(words), error_positions


def generate_training_examples(num_examples: int = 10000) -> List[dict]:
    """Generate training examples with labels."""
    examples = []

    for _ in range(num_examples):
        # Pick random base sentence
        sentence = random.choice(BASE_SENTENCES)

        # Corrupt it
        corrupted, error_positions = corrupt_sentence(sentence)

        # Create BIO labels (0 = O, 1 = B-ERROR)
        # Note: We use simplified labeling (no I-ERROR for multi-word errors)
        words = corrupted.split()
        labels = [1 if i in error_positions else 0 for i in range(len(words))]

        examples.append({
            'text': corrupted,
            'labels': labels,
            'num_errors': len(error_positions),
        })

    return examples


def main():
    """Generate and save training/validation datasets."""
    print("Generating dyslexic error dataset...")

    # Generate examples
    train_examples = generate_training_examples(8000)
    val_examples = generate_training_examples(2000)

    # Create output directory
    data_dir = Path(__file__).parent / 'data'
    data_dir.mkdir(exist_ok=True)

    # Save as JSONL
    train_file = data_dir / 'train.jsonl'
    val_file = data_dir / 'val.jsonl'

    with open(train_file, 'w') as f:
        for ex in train_examples:
            f.write(json.dumps(ex) + '\n')

    with open(val_file, 'w') as f:
        for ex in val_examples:
            f.write(json.dumps(ex) + '\n')

    print(f"✓ Generated {len(train_examples)} training examples")
    print(f"✓ Generated {len(val_examples)} validation examples")
    print(f"✓ Saved to {data_dir}")

    # Print sample
    print("\nSample corrupted sentences:")
    for i in range(5):
        ex = train_examples[i]
        words = ex['text'].split()
        highlighted = []
        for j, word in enumerate(words):
            if ex['labels'][j] == 1:
                highlighted.append(f"[{word}]")
            else:
                highlighted.append(word)
        print(f"  {' '.join(highlighted)}")


if __name__ == '__main__':
    main()
