"""Shared fixtures for ML pipeline tests."""

import json
import sys
from pathlib import Path

import pytest

# Ensure the project root is importable so we can do `from ml.datasets...`
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


# ---------------------------------------------------------------------------
# Word-pair fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_word_pairs() -> list[tuple[str, str]]:
    """List of (misspelling, correct) tuples covering various error types."""
    return [
        ("teh", "the"),
        ("form", "from"),
        ("becuase", "because"),
        ("wich", "which"),
        ("whn", "when"),
        ("fone", "phone"),
        ("bog", "dog"),
        ("whhen", "when"),
        ("recieve", "receive"),
        ("beutiful", "beautiful"),
        ("accomodate", "accommodate"),
        ("seperate", "separate"),
    ]


@pytest.fixture
def sample_sentences() -> list[str]:
    """List of clean sentences for error injection testing."""
    return [
        "The quick brown fox jumps over the lazy dog.",
        "She went to the store to buy some bread.",
        "When you arrive at the house please phone me.",
        "The dog ran from the park which was closed.",
        "He said he would arrive because he had time.",
        "They asked when the meeting would begin.",
        "The beautiful garden was full of flowers.",
        "We need to accommodate all the guests.",
        "Please separate the items into two piles.",
        "I will receive the package tomorrow.",
    ]


# ---------------------------------------------------------------------------
# Temporary directory fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_raw_dir(tmp_path: Path) -> Path:
    """Temporary directory for raw dataset files."""
    d = tmp_path / "raw"
    d.mkdir()
    return d


@pytest.fixture
def tmp_processed_dir(tmp_path: Path) -> Path:
    """Temporary directory for processed dataset files."""
    d = tmp_path / "processed"
    d.mkdir()
    return d


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """Temporary directory for final output files."""
    d = tmp_path / "output"
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# File-format fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def birkbeck_file(tmp_raw_dir: Path) -> Path:
    """Create a temp Birkbeck-format file with known content.

    Birkbeck format:
        $correct_word
        misspelling1
        misspelling2
        $another_correct
        misspelling3
    """
    filepath = tmp_raw_dir / "birkbeck_missp.dat"
    content = (
        "$the\n"
        "teh\n"
        "hte\n"
        "$from\n"
        "form\n"
        "fomr\n"
        "$because\n"
        "becuase\n"
        "becasue\n"
        "$which\n"
        "wich\n"
        "$when\n"
        "whn\n"
        "$phone\n"
        "fone\n"
    )
    filepath.write_text(content)
    return filepath


@pytest.fixture
def wikipedia_file(tmp_raw_dir: Path) -> Path:
    """Create a temp Wikipedia-format file with known content.

    Wikipedia raw wikitext format:
        misspelling->correct
    """
    filepath = tmp_raw_dir / "wikipedia_misspellings.txt"
    content = (
        " accomodate->accommodate\n"
        " adress->address\n"
        " aparent->apparent\n"
        " beleive->believe\n"
        " calender->calendar\n"
        " definately->definitely\n"
        " enviroment->environment\n"
        " foriegn->foreign\n"
        " goverment->government\n"
        " harrass->harass\n"
        " independant->independent\n"
        " judgement->judgment\n"
        " knowlege->knowledge\n"
        " liason->liaison\n"
        " millenium->millennium\n"
        " neccessary->necessary\n"
        " occurence->occurrence\n"
        " perseverence->perseverance\n"
        " questionaire->questionnaire\n"
        " recieve->receive\n"
        " seperate->separate\n"
        " tendancy->tendency\n"
        " underate->underrate\n"
        " vacum->vacuum\n"
        " wierd->weird\n"
        " existance->existence\n"
        " occurrance->occurrence\n"
        " persistance->persistence\n"
        " resistence->resistance\n"
        " absense->absence\n"
        " acheive->achieve\n"
        " agressive->aggressive\n"
        " amature->amateur\n"
        " arguement->argument\n"
        " assasinate->assassinate\n"
        " basicly->basically\n"
        " begining->beginning\n"
        " buisness->business\n"
        " camoflage->camouflage\n"
        " catagory->category\n"
        " changable->changeable\n"
        " cheif->chief\n"
        " collegue->colleague\n"
        " comming->coming\n"
        " commitee->committee\n"
        " completly->completely\n"
        " concious->conscious\n"
        " congradulate->congratulate\n"
        " consciencious->conscientious\n"
        " concensus->consensus\n"
        " contraversy->controversy\n"
        " convienient->convenient\n"
        " decieve->deceive\n"
        " desireable->desirable\n"
        " desparate->desperate\n"
        " develope->develop\n"
        " dilemna->dilemma\n"
        " disapear->disappear\n"
        " disapoint->disappoint\n"
        " ecstacy->ecstasy\n"
        " embarass->embarrass\n"
        " excede->exceed\n"
        " existance->existence\n"
        " experiance->experience\n"
        " facinate->fascinate\n"
        " familar->familiar\n"
        " finaly->finally\n"
        " flourescent->fluorescent\n"
        " forteen->fourteen\n"
        " freind->friend\n"
        " gaurd->guard\n"
        " geneology->genealogy\n"
        " gratefull->grateful\n"
        " garantee->guarantee\n"
        " happyness->happiness\n"
        " heighth->height\n"
        " heirarchy->hierarchy\n"
        " humourous->humorous\n"
        " hygeine->hygiene\n"
        " ignorence->ignorance\n"
        " immediatly->immediately\n"
        " incidently->incidentally\n"
        " independance->independence\n"
        " innoculate->inoculate\n"
        " inteligence->intelligence\n"
        " iresistable->irresistible\n"
        " jealosy->jealousy\n"
        " jewlery->jewelry\n"
        " kernell->kernel\n"
        " liesure->leisure\n"
        " libary->library\n"
        " lisence->license\n"
        " lonelyness->loneliness\n"
        " maintenence->maintenance\n"
        " manuever->maneuver\n"
        " medeval->medieval\n"
        " memento->memento\n"
        " milege->mileage\n"
        " miniscule->minuscule\n"
        " mischievious->mischievous\n"
        " mispell->misspell\n"
    )
    filepath.write_text(content)
    return filepath


# ---------------------------------------------------------------------------
# Training data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_training_data() -> list[dict]:
    """List of dicts in labels format (as used by training pipeline)."""
    return [
        {
            "text": "teh cat sat on the mat",
            "labels": [1, 0, 0, 0, 0, 0],
            "source": "birkbeck",
            "error_type": "transposition",
        },
        {
            "text": "the cat sat on teh mat",
            "labels": [0, 0, 0, 0, 1, 0],
            "source": "birkbeck",
            "error_type": "transposition",
        },
        {
            "text": "she went to the store",
            "labels": [0, 0, 0, 0, 0],
            "source": "birkbeck",
            "error_type": "none",
        },
        {
            "text": "wich way do we go",
            "labels": [1, 0, 0, 0, 0],
            "source": "wikipedia",
            "error_type": "omission",
        },
        {
            "text": "he foned the office yesterday",
            "labels": [0, 1, 0, 0, 0],
            "source": "synthetic",
            "error_type": "phonetic",
        },
    ]


@pytest.fixture
def sample_synthetic_data() -> list[dict]:
    """List of dicts in corrections format (as produced by SyntheticDataGenerator)."""
    return [
        {
            "text": "teh quick brown fox",
            "clean_text": "the quick brown fox",
            "corrections": [
                {
                    "start": 0,
                    "end": 3,
                    "original": "teh",
                    "corrected": "the",
                    "type": "transposition",
                    "confidence": 1.0,
                }
            ],
        },
        {
            "text": "she went to teh store",
            "clean_text": "she went to the store",
            "corrections": [
                {
                    "start": 12,
                    "end": 15,
                    "original": "teh",
                    "corrected": "the",
                    "type": "transposition",
                    "confidence": 1.0,
                }
            ],
        },
        {
            "text": "the bog ran fast",
            "clean_text": "the dog ran fast",
            "corrections": [
                {
                    "start": 4,
                    "end": 7,
                    "original": "bog",
                    "corrected": "dog",
                    "type": "reversal",
                    "confidence": 1.0,
                }
            ],
        },
    ]
