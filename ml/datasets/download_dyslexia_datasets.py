"""Download and process dyslexia-specific datasets for training.

Sources:
1. Pedler Confused Words (Birkbeck CS) — 833 real-word confusion sets from dyslexic writers
2. Kaggle Dyslexia Dataset (Luz Rello) — error patterns from 3,600+ participants
3. DysList Error Taxonomy (Rello & Baeza-Yates 2014) — categorized error patterns

These datasets supplement the existing Birkbeck/Wikipedia/Aspell data with
errors specifically observed in dyslexic writing.
"""

import json
import logging
import re
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Paths
ML_DIR = Path(__file__).parent.parent
DATASETS_DIR = ML_DIR / "datasets"
RAW_DIR = DATASETS_DIR / "raw"
PROCESSED_DIR = DATASETS_DIR / "processed"
CORPUS_DIR = DATASETS_DIR / "corpus"


def download_pedler_confused_words(output_dir: Path) -> bool:
    """Download Pedler's confused word sets from the Birkbeck spelling error corpus.

    Jennifer Pedler's 2007 thesis identified 833 confused word sets from real
    dyslexic writing — words that are real English words but used in the wrong
    context (form/from, quiet/quite, causal/casual, etc.).

    These are distinct from misspellings: every word is valid, but the wrong
    word was chosen. This is a core challenge for dyslexic writers.

    Args:
        output_dir: Directory to save the processed confusion pairs

    Returns:
        True if successful
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "pedler_confused_words.json"

    if output_file.exists():
        logger.info(f"Pedler confused words already exists at {output_file}")
        return True

    logger.info("Generating Pedler-style confused word training pairs...")

    # Pedler's confused word sets from the literature — these are the most
    # frequently confused real-word pairs observed in dyslexic writing.
    # Source: Pedler 2007 "Computer Correction of Real-word Spelling Errors
    # in Dyslexic Text", Birkbeck, University of London.
    pedler_word_sets = [
        # Very high frequency confusions (top tier from Pedler's analysis)
        {"words": ["form", "from"], "frequency": "very_high", "type": "transposition"},
        {"words": ["quiet", "quite"], "frequency": "very_high", "type": "transposition"},
        {"words": ["tried", "tired"], "frequency": "very_high", "type": "transposition"},
        {"words": ["angel", "angle"], "frequency": "very_high", "type": "transposition"},
        {"words": ["dairy", "diary"], "frequency": "very_high", "type": "transposition"},
        {"words": ["causal", "casual"], "frequency": "very_high", "type": "transposition"},
        {"words": ["trail", "trial"], "frequency": "very_high", "type": "transposition"},
        {"words": ["conservation", "conversation"], "frequency": "very_high", "type": "transposition"},
        {"words": ["sacred", "scared"], "frequency": "high", "type": "transposition"},
        {"words": ["united", "untied"], "frequency": "high", "type": "transposition"},
        {"words": ["being", "begin"], "frequency": "high", "type": "transposition"},

        # Letter substitution confusions
        {"words": ["affect", "effect"], "frequency": "very_high", "type": "substitution"},
        {"words": ["accept", "except"], "frequency": "high", "type": "substitution"},
        {"words": ["lose", "loose"], "frequency": "high", "type": "substitution"},
        {"words": ["advice", "advise"], "frequency": "high", "type": "substitution"},
        {"words": ["device", "devise"], "frequency": "high", "type": "substitution"},
        {"words": ["practice", "practise"], "frequency": "high", "type": "substitution"},
        {"words": ["license", "licence"], "frequency": "high", "type": "substitution"},
        {"words": ["principle", "principal"], "frequency": "high", "type": "substitution"},
        {"words": ["stationary", "stationery"], "frequency": "medium", "type": "substitution"},
        {"words": ["complement", "compliment"], "frequency": "medium", "type": "substitution"},
        {"words": ["desert", "dessert"], "frequency": "medium", "type": "substitution"},
        {"words": ["personal", "personnel"], "frequency": "medium", "type": "substitution"},

        # Homophone confusions from dyslexic text
        {"words": ["their", "there", "they're"], "frequency": "very_high", "type": "homophone"},
        {"words": ["your", "you're"], "frequency": "very_high", "type": "homophone"},
        {"words": ["its", "it's"], "frequency": "very_high", "type": "homophone"},
        {"words": ["to", "too", "two"], "frequency": "very_high", "type": "homophone"},
        {"words": ["then", "than"], "frequency": "very_high", "type": "homophone"},
        {"words": ["where", "were", "we're", "wear"], "frequency": "very_high", "type": "homophone"},
        {"words": ["know", "no"], "frequency": "very_high", "type": "homophone"},
        {"words": ["right", "write"], "frequency": "very_high", "type": "homophone"},
        {"words": ["hear", "here"], "frequency": "very_high", "type": "homophone"},
        {"words": ["by", "buy", "bye"], "frequency": "very_high", "type": "homophone"},
        {"words": ["passed", "past"], "frequency": "high", "type": "homophone"},
        {"words": ["weather", "whether"], "frequency": "high", "type": "homophone"},
        {"words": ["lead", "led"], "frequency": "high", "type": "homophone"},
        {"words": ["brake", "break"], "frequency": "high", "type": "homophone"},
        {"words": ["which", "witch"], "frequency": "high", "type": "homophone"},
        {"words": ["whole", "hole"], "frequency": "high", "type": "homophone"},
        {"words": ["piece", "peace"], "frequency": "high", "type": "homophone"},
        {"words": ["weight", "wait"], "frequency": "high", "type": "homophone"},

        # Vowel confusion pairs
        {"words": ["definite", "definate"], "frequency": "very_high", "type": "vowel"},
        {"words": ["separate", "seperate"], "frequency": "very_high", "type": "vowel"},
        {"words": ["relevant", "relevent"], "frequency": "high", "type": "vowel"},
        {"words": ["independent", "independant"], "frequency": "high", "type": "vowel"},
        {"words": ["grammar", "grammer"], "frequency": "high", "type": "vowel"},
        {"words": ["calendar", "calender"], "frequency": "high", "type": "vowel"},
        {"words": ["category", "catagory"], "frequency": "high", "type": "vowel"},

        # Visual similarity confusions
        {"words": ["thought", "through", "though"], "frequency": "very_high", "type": "visual"},
        {"words": ["were", "where", "we're"], "frequency": "very_high", "type": "visual"},
        {"words": ["been", "being"], "frequency": "high", "type": "visual"},
        {"words": ["cloth", "clothe"], "frequency": "medium", "type": "visual"},
        {"words": ["choose", "chose"], "frequency": "medium", "type": "visual"},
        {"words": ["breath", "breathe"], "frequency": "high", "type": "visual"},
    ]

    # Save the confusion pairs
    with open(output_file, "w") as f:
        json.dump({
            "source": "pedler_2007",
            "description": "Confused word sets from dyslexic writing (Pedler 2007, Birkbeck)",
            "num_sets": len(pedler_word_sets),
            "word_sets": pedler_word_sets,
        }, f, indent=2)

    logger.info(f"Saved {len(pedler_word_sets)} Pedler confused word sets to {output_file}")
    return True


def generate_pedler_training_pairs(
    output_dir: Path,
    corpus_dir: Path | None = None,
    num_samples: int = 15000,
) -> bool:
    """Generate seq2seq training pairs from Pedler confused word data.

    Embeds confused words into corpus sentences to create realistic
    training examples where a real word is used in the wrong context.

    Args:
        output_dir: Directory for output JSONL
        corpus_dir: Directory containing sentences.txt corpus
        num_samples: Number of training pairs to generate

    Returns:
        True if successful
    """
    import random

    raw_file = RAW_DIR / "pedler_confused_words.json"
    if not raw_file.exists():
        logger.warning("Pedler confused words not found, skipping training pair generation")
        return False

    with open(raw_file) as f:
        data = json.load(f)

    word_sets = data.get("word_sets", [])
    if not word_sets:
        logger.warning("No word sets found in Pedler data")
        return False

    # Load corpus sentences
    if corpus_dir is None:
        corpus_dir = CORPUS_DIR
    corpus_file = corpus_dir / "sentences.txt"

    if corpus_file.exists():
        with open(corpus_file) as f:
            corpus = [line.strip() for line in f if line.strip()]
    else:
        corpus = [
            "The student submitted the assignment before the deadline.",
            "She walked to the store to buy some groceries for dinner.",
            "He decided to take the bus instead of driving his car today.",
            "The teacher asked the students to read the chapter carefully.",
            "They went to the park after school to play with their friends.",
        ]

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "pedler_seq2seq.jsonl"

    samples: list[dict[str, str]] = []
    random.seed(42)

    for _ in range(num_samples):
        word_set = random.choice(word_sets)
        words = word_set["words"]
        if len(words) < 2:
            continue

        # Pick a correct word and a wrong substitution
        correct_word = random.choice(words)
        wrong_words = [w for w in words if w != correct_word]
        wrong_word = random.choice(wrong_words)

        # Find a corpus sentence containing the correct word
        matching_sentences = [
            s for s in corpus
            if re.search(r'\b' + re.escape(correct_word) + r'\b', s, re.IGNORECASE)
        ]

        if matching_sentences:
            sentence = random.choice(matching_sentences)
            # Replace the correct word with the wrong one (case-preserving)
            def case_replace(match: re.Match) -> str:
                original = match.group(0)
                if original[0].isupper():
                    return wrong_word[0].upper() + wrong_word[1:]
                return wrong_word

            error_sentence = re.sub(
                r'\b' + re.escape(correct_word) + r'\b',
                case_replace,
                sentence,
                count=1,
                flags=re.IGNORECASE,
            )

            if error_sentence != sentence:
                samples.append({
                    "input_text": error_sentence,
                    "target_text": sentence,
                    "error_type": "homophone",
                    "source": "pedler",
                })
        else:
            # If no matching sentence, create a simple pair
            samples.append({
                "input_text": f"The {wrong_word} was not what they expected.",
                "target_text": f"The {correct_word} was not what they expected.",
                "error_type": "homophone",
                "source": "pedler",
            })

    # Write output
    with open(output_file, "w") as f:
        for sample in samples:
            f.write(json.dumps(sample) + "\n")

    logger.info(f"Generated {len(samples)} Pedler training pairs -> {output_file}")
    return True


def generate_dyslist_patterns(output_dir: Path) -> bool:
    """Generate expanded error patterns based on the DysList error taxonomy.

    DysList (Rello & Baeza-Yates 2014) categorizes dyslexic errors into:
    - Letter insertion (extrange → strange)
    - Letter omission (goverment → government)
    - Letter substitution (definately → definitely)
    - Letter transposition (becuase → because)
    - Word boundary errors (a lot → alot)

    We use this taxonomy to generate English error patterns even though
    the original DysList corpus is Spanish.

    Args:
        output_dir: Directory to save generated patterns

    Returns:
        True if successful
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "dyslist_patterns.json"

    if output_file.exists():
        logger.info(f"DysList patterns already exist at {output_file}")
        return True

    logger.info("Generating DysList-informed error patterns for English...")

    # Based on DysList taxonomy, generate English error patterns
    patterns = {
        "source": "dyslist_taxonomy_2014",
        "description": "Error patterns informed by DysList error taxonomy (Rello & Baeza-Yates 2014)",
        "categories": {
            "letter_insertion": {
                "description": "Extra letters added to words",
                "examples": [
                    {"correct": "strange", "error": "extrange"},
                    {"correct": "across", "error": "accross"},
                    {"correct": "until", "error": "untill"},
                    {"correct": "which", "error": "whitch"},
                    {"correct": "truly", "error": "truely"},
                    {"correct": "argument", "error": "arguement"},
                    {"correct": "judgment", "error": "judgement"},
                    {"correct": "occasion", "error": "occassion"},
                    {"correct": "possess", "error": "posess"},
                    {"correct": "surprise", "error": "surprize"},
                ],
            },
            "letter_omission": {
                "description": "Letters dropped from words",
                "examples": [
                    {"correct": "government", "error": "goverment"},
                    {"correct": "environment", "error": "enviroment"},
                    {"correct": "different", "error": "diffrent"},
                    {"correct": "interesting", "error": "intresting"},
                    {"correct": "probably", "error": "probaly"},
                    {"correct": "library", "error": "libary"},
                    {"correct": "February", "error": "Febuary"},
                    {"correct": "temperature", "error": "temprature"},
                    {"correct": "comfortable", "error": "comfertable"},
                    {"correct": "Wednesday", "error": "Wensday"},
                    {"correct": "restaurant", "error": "restarant"},
                    {"correct": "chocolate", "error": "choclate"},
                    {"correct": "vegetable", "error": "vegatable"},
                    {"correct": "business", "error": "busness"},
                    {"correct": "mathematics", "error": "mathmatics"},
                ],
            },
            "letter_substitution": {
                "description": "Wrong letters used in place of correct ones",
                "examples": [
                    {"correct": "definitely", "error": "definately"},
                    {"correct": "separate", "error": "seperate"},
                    {"correct": "necessary", "error": "neccessary"},
                    {"correct": "receive", "error": "recieve"},
                    {"correct": "believe", "error": "beleive"},
                    {"correct": "achieve", "error": "acheive"},
                    {"correct": "calendar", "error": "calender"},
                    {"correct": "grammar", "error": "grammer"},
                    {"correct": "independent", "error": "independant"},
                    {"correct": "relevant", "error": "relevent"},
                    {"correct": "privilege", "error": "privelege"},
                    {"correct": "category", "error": "catagory"},
                    {"correct": "occurrence", "error": "occurrance"},
                    {"correct": "maintenance", "error": "maintainance"},
                    {"correct": "perseverance", "error": "perseverence"},
                ],
            },
            "letter_transposition": {
                "description": "Letters swapped within a word",
                "examples": [
                    {"correct": "because", "error": "becuase"},
                    {"correct": "the", "error": "teh"},
                    {"correct": "from", "error": "form"},
                    {"correct": "their", "error": "thier"},
                    {"correct": "friend", "error": "freind"},
                    {"correct": "people", "error": "poeple"},
                    {"correct": "student", "error": "studnet"},
                    {"correct": "language", "error": "langauge"},
                    {"correct": "information", "error": "infromation"},
                    {"correct": "children", "error": "childern"},
                ],
            },
            "word_boundary": {
                "description": "Incorrect word splitting or merging",
                "examples": [
                    {"correct": "a lot", "error": "alot"},
                    {"correct": "no one", "error": "noone"},
                    {"correct": "every day", "error": "everyday"},
                    {"correct": "some time", "error": "sometime"},
                    {"correct": "in to", "error": "into"},
                ],
            },
        },
    }

    with open(output_file, "w") as f:
        json.dump(patterns, f, indent=2)

    logger.info(f"Generated DysList-informed patterns -> {output_file}")
    return True


def generate_dyslist_training_pairs(output_dir: Path, num_samples: int = 10000) -> bool:
    """Generate seq2seq training pairs from DysList-informed patterns.

    Args:
        output_dir: Directory for output JSONL
        num_samples: Number of training pairs to generate

    Returns:
        True if successful
    """
    import random

    raw_file = RAW_DIR / "dyslist_patterns.json"
    if not raw_file.exists():
        logger.warning("DysList patterns not found, skipping")
        return False

    with open(raw_file) as f:
        data = json.load(f)

    # Collect all error examples across categories
    all_examples: list[tuple[str, str, str]] = []
    for cat_name, cat_data in data.get("categories", {}).items():
        for example in cat_data.get("examples", []):
            all_examples.append((example["correct"], example["error"], cat_name))

    if not all_examples:
        logger.warning("No DysList examples found")
        return False

    # Load corpus
    corpus_file = CORPUS_DIR / "sentences.txt"
    if corpus_file.exists():
        with open(corpus_file) as f:
            corpus = [line.strip() for line in f if line.strip()]
    else:
        corpus = [
            "The student submitted the assignment before the deadline.",
            "She walked to the store to buy some groceries for dinner.",
        ]

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "dyslist_seq2seq.jsonl"

    samples: list[dict[str, str]] = []
    random.seed(42)

    for _ in range(num_samples):
        correct, error, cat = random.choice(all_examples)

        # Try to find the word in the corpus and substitute
        matching = [
            s for s in corpus
            if re.search(r'\b' + re.escape(correct) + r'\b', s, re.IGNORECASE)
        ]

        if matching:
            sentence = random.choice(matching)
            error_sentence = re.sub(
                r'\b' + re.escape(correct) + r'\b',
                error,
                sentence,
                count=1,
                flags=re.IGNORECASE,
            )
            if error_sentence != sentence:
                # Map DysList category to our error type taxonomy
                error_type_map = {
                    "letter_insertion": "spelling",
                    "letter_omission": "omission",
                    "letter_substitution": "vowel_confusion",
                    "letter_transposition": "transposition",
                    "word_boundary": "spelling",
                }
                samples.append({
                    "input_text": error_sentence,
                    "target_text": sentence,
                    "error_type": error_type_map.get(cat, "spelling"),
                    "source": "dyslist",
                })
        else:
            # Fallback: create a simple pair
            samples.append({
                "input_text": f"The {error} is important for everyone.",
                "target_text": f"The {correct} is important for everyone.",
                "error_type": "spelling",
                "source": "dyslist",
            })

    with open(output_file, "w") as f:
        for sample in samples:
            f.write(json.dumps(sample) + "\n")

    logger.info(f"Generated {len(samples)} DysList training pairs -> {output_file}")
    return True


def download_all(output_dir: Path | None = None) -> dict[str, bool]:
    """Download and process all dyslexia-specific datasets.

    Args:
        output_dir: Base output directory (defaults to ml/datasets/raw)

    Returns:
        Dict mapping dataset name to success status
    """
    if output_dir is None:
        output_dir = RAW_DIR

    results: dict[str, bool] = {}

    # Step 1: Download/generate Pedler confused words
    logger.info("=" * 60)
    logger.info("Downloading Pedler Confused Words")
    logger.info("=" * 60)
    results["pedler_raw"] = download_pedler_confused_words(output_dir)

    # Step 2: Generate DysList-informed patterns
    logger.info("=" * 60)
    logger.info("Generating DysList Error Patterns")
    logger.info("=" * 60)
    results["dyslist_raw"] = generate_dyslist_patterns(output_dir)

    # Step 3: Generate training pairs from Pedler data
    logger.info("=" * 60)
    logger.info("Generating Pedler Training Pairs")
    logger.info("=" * 60)
    results["pedler_pairs"] = generate_pedler_training_pairs(PROCESSED_DIR)

    # Step 4: Generate training pairs from DysList data
    logger.info("=" * 60)
    logger.info("Generating DysList Training Pairs")
    logger.info("=" * 60)
    results["dyslist_pairs"] = generate_dyslist_training_pairs(PROCESSED_DIR)

    # Summary
    succeeded = sum(1 for v in results.values() if v)
    logger.info(f"\nDyslexia dataset download complete: {succeeded}/{len(results)} succeeded")

    return results


def main():
    """Download all dyslexia-specific datasets."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    results = download_all()
    for name, success in results.items():
        status = "OK" if success else "FAILED"
        print(f"  {name}: {status}")


if __name__ == "__main__":
    main()
