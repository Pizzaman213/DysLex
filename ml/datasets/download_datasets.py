"""Download real-world misspelling datasets for training.

Downloads:
  - Birkbeck spelling error corpus
  - Aspell word list test data
  - Wikipedia common misspellings
  - GitHub Typo Corpus

If files already exist locally, they are skipped.
"""

import gzip
import logging
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

DATASETS = {
    "birkbeck": {
        "url": "https://www.dcs.bbk.ac.uk/~ROGER/missp.dat",
        "filename": "birkbeck_missp.dat",
    },
    "aspell": {
        "url": "https://www.dcs.bbk.ac.uk/~ROGER/aspell.dat",
        "filename": "aspell.dat",
    },
    "wikipedia": {
        "url": "https://en.wikipedia.org/wiki/Wikipedia:Lists_of_common_misspellings/For_machines",
        "filename": "wikipedia_misspellings.txt",
    },
    "github_typo": {
        "url": "https://github-typo-corpus.s3.amazonaws.com/data/github-typo-corpus.v1.0.0.jsonl.gz",
        "filename": "github_typo_corpus.jsonl.gz",
    },
    "tatoeba": {
        "url": "https://downloads.tatoeba.org/exports/sentences.tar.bz2",
        "filename": "tatoeba_sentences.tar.bz2",
    },
}


def download_all(output_dir: Path) -> dict[str, bool]:
    """Download all datasets to output_dir.

    Args:
        output_dir: Directory to save downloaded files

    Returns:
        Dict mapping dataset name to success boolean
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, bool] = {}

    for name, info in DATASETS.items():
        filepath = output_dir / info["filename"]
        if filepath.exists() and filepath.stat().st_size > 0:
            logger.info(f"  {name}: already exists ({filepath.stat().st_size:,} bytes), skipping")
            results[name] = True
            continue

        logger.info(f"  {name}: downloading from {info['url']}...")
        try:
            urllib.request.urlretrieve(info["url"], filepath)
            logger.info(f"  {name}: saved to {filepath} ({filepath.stat().st_size:,} bytes)")
            results[name] = True
        except Exception as e:
            logger.warning(f"  {name}: download failed: {e}")
            results[name] = False

    return results
