"""Download and prepare diverse sentence corpus for synthetic error generation.

Sources:
  - Tatoeba English sentences (CC-BY, diverse community-contributed sentences)
  - Simple Wikipedia (accessible language, shorter sentences)
  - Existing generate_sentences.py output (template-generated)

Filters sentences to:
  - English only
  - 5-30 words (good length for error generation)
  - No URLs, special characters, or non-ASCII
  - Deduplicated

Target: 20,000-50,000 diverse sentences
"""

import logging
import os
import random
import re
import tarfile
from pathlib import Path

logger = logging.getLogger(__name__)

random.seed(42)

CORPUS_DIR = Path(__file__).parent / "corpus"
RAW_DIR = Path(__file__).parent / "raw"

# Sentence quality filters
MIN_WORDS = 5
MAX_WORDS = 30
MAX_CHAR_LENGTH = 200


def _is_good_sentence(text: str) -> bool:
    """Check if a sentence meets quality criteria for training data."""
    text = text.strip()
    if not text:
        return False

    # Must end with sentence-ending punctuation
    if not text[-1] in ".!?":
        return False

    # Must start with uppercase
    if not text[0].isupper():
        return False

    # Word count check
    words = text.split()
    if len(words) < MIN_WORDS or len(words) > MAX_WORDS:
        return False

    # Length check
    if len(text) > MAX_CHAR_LENGTH:
        return False

    # No URLs
    if "http" in text or "www." in text:
        return False

    # ASCII only (no accented chars that confuse the model)
    try:
        text.encode("ascii")
    except UnicodeEncodeError:
        return False

    # No tabs, multiple spaces, or other artifacts
    if "\t" in text or "  " in text:
        return False

    # No brackets, braces, or other non-prose characters
    if re.search(r"[\[\]{}<>|\\@#$%^&*_~`]", text):
        return False

    return True


def extract_tatoeba_english(
    raw_dir: Path = RAW_DIR,
    max_sentences: int = 30000,
) -> list[str]:
    """Extract English sentences from Tatoeba tarball.

    The Tatoeba export contains a TSV file with: id, lang, text
    We filter for lang='eng' and apply quality checks.

    Args:
        raw_dir: Directory containing tatoeba_sentences.tar.bz2
        max_sentences: Maximum number of sentences to extract

    Returns:
        List of clean English sentences
    """
    tarball = raw_dir / "tatoeba_sentences.tar.bz2"
    if not tarball.exists():
        logger.warning(f"Tatoeba data not found at {tarball}. Run --download first.")
        return []

    logger.info("Extracting English sentences from Tatoeba...")
    sentences = []

    try:
        with tarfile.open(tarball, "r:bz2") as tar:
            for member in tar.getmembers():
                if "sentences" in member.name and member.name.endswith(".csv"):
                    f = tar.extractfile(member)
                    if f is None:
                        continue
                    for line_bytes in f:
                        line = line_bytes.decode("utf-8", errors="ignore").strip()
                        parts = line.split("\t")
                        if len(parts) >= 3 and parts[1] == "eng":
                            text = parts[2].strip()
                            if _is_good_sentence(text):
                                sentences.append(text)
                                if len(sentences) >= max_sentences * 2:
                                    break
                    break
    except Exception as e:
        logger.warning(f"Failed to extract Tatoeba: {e}")
        return []

    # Deduplicate and sample
    sentences = list(set(sentences))
    random.shuffle(sentences)
    sentences = sentences[:max_sentences]

    logger.info(f"Extracted {len(sentences)} English sentences from Tatoeba")
    return sentences


def download_simple_wikipedia_sentences(
    max_sentences: int = 20000,
) -> list[str]:
    """Fetch sentences from Simple English Wikipedia random articles.

    Uses the Wikipedia API to get random articles from Simple English Wikipedia,
    which uses accessible language ideal for dyslexic writing training.

    Args:
        max_sentences: Maximum number of sentences to collect

    Returns:
        List of clean sentences
    """
    import json
    import urllib.request

    logger.info("Fetching sentences from Simple English Wikipedia...")
    sentences: list[str] = []
    seen: set[str] = set()

    # Fetch random articles and extract sentences
    api_url = (
        "https://simple.wikipedia.org/w/api.php?"
        "action=query&generator=random&grnnamespace=0&grnlimit=50"
        "&prop=extracts&exlimit=50&explaintext=1&format=json"
    )

    attempts = 0
    max_attempts = 100  # Limit API calls

    while len(sentences) < max_sentences and attempts < max_attempts:
        attempts += 1
        try:
            req = urllib.request.Request(
                api_url,
                headers={"User-Agent": "DysLexAI-Training/1.0 (educational)"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.warning(f"Wikipedia API request failed: {e}")
            break

        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            text = page.get("extract", "")
            if not text:
                continue

            # Split into sentences (simple heuristic)
            for sent in re.split(r"(?<=[.!?])\s+", text):
                sent = sent.strip()
                if _is_good_sentence(sent) and sent.lower() not in seen:
                    seen.add(sent.lower())
                    sentences.append(sent)

        if (attempts % 10) == 0:
            logger.info(f"  Collected {len(sentences)} sentences so far...")

    sentences = sentences[:max_sentences]
    logger.info(f"Collected {len(sentences)} sentences from Simple Wikipedia")
    return sentences


def build_expanded_corpus(
    output_file: Path | None = None,
    target_total: int = 30000,
    include_tatoeba: bool = True,
    include_simple_wiki: bool = True,
) -> list[str]:
    """Build an expanded sentence corpus from multiple sources.

    Combines:
    1. Existing template-generated sentences (~5K)
    2. Tatoeba English sentences (up to 20K)
    3. Simple Wikipedia sentences (up to 15K)

    Args:
        output_file: Path to write the combined corpus
        target_total: Target total sentences
        include_tatoeba: Whether to include Tatoeba sentences
        include_simple_wiki: Whether to include Simple Wikipedia

    Returns:
        List of all sentences
    """
    if output_file is None:
        output_file = CORPUS_DIR / "sentences.txt"

    all_sentences: list[str] = []
    seen: set[str] = set()

    def _add_unique(sentences: list[str], source: str) -> int:
        """Add unique sentences, return count added."""
        added = 0
        for s in sentences:
            key = s.lower().strip()
            if key not in seen:
                seen.add(key)
                all_sentences.append(s.strip())
                added += 1
        logger.info(f"  {source}: added {added} unique sentences")
        return added

    # Source 1: Existing corpus
    existing_corpus = CORPUS_DIR / "sentences.txt"
    if existing_corpus.exists():
        with open(existing_corpus) as f:
            existing = [line.strip() for line in f if line.strip()]
        _add_unique(existing, "existing corpus")

    # Source 2: Tatoeba
    if include_tatoeba:
        remaining = target_total - len(all_sentences)
        if remaining > 0:
            tatoeba = extract_tatoeba_english(max_sentences=min(remaining, 20000))
            _add_unique(tatoeba, "Tatoeba")

    # Source 3: Simple Wikipedia
    if include_simple_wiki:
        remaining = target_total - len(all_sentences)
        if remaining > 0:
            wiki = download_simple_wikipedia_sentences(max_sentences=min(remaining, 15000))
            _add_unique(wiki, "Simple Wikipedia")

    random.shuffle(all_sentences)
    all_sentences = all_sentences[:target_total]

    # Write output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        for s in all_sentences:
            f.write(s + "\n")

    logger.info(f"Expanded corpus: {len(all_sentences)} sentences -> {output_file}")
    return all_sentences


def main():
    """Build expanded sentence corpus."""
    logging.basicConfig(level=logging.INFO)
    corpus = build_expanded_corpus(target_total=30000)
    print(f"\nCorpus built: {len(corpus)} sentences")
    if corpus:
        print(f"\nSamples:")
        for s in random.sample(corpus, min(5, len(corpus))):
            print(f"  {s}")


if __name__ == "__main__":
    main()
