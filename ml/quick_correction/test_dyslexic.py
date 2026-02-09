"""Test the Quick Correction models on realistic dyslexic writing samples.

Runs both the seq2seq model (T5-small) and the ONNX token-classification model
against hand-crafted dyslexic sentences organized by error category, then
reports per-category and overall accuracy, latency, and sample-level details.

Usage:
    cd /Users/connorsecrist/Dyslexia
    python ml/quick_correction/test_dyslexic.py
    python ml/quick_correction/test_dyslexic.py --verbose
    python ml/quick_correction/test_dyslexic.py --seq2seq-only
    python ml/quick_correction/test_dyslexic.py --onnx-only
"""

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Model paths
SEQ2SEQ_MODEL_DIR = PROJECT_ROOT / "ml" / "quick_correction" / "models" / "quick_correction_seq2seq_v1"
ONNX_MODEL_DIR = PROJECT_ROOT / "ml" / "models" / "quick_correction_base_v1"

# -------------------------------------------------------------------------
# Dyslexic test sentences — real-world patterns
# -------------------------------------------------------------------------

@dataclass
class TestSample:
    category: str
    input_text: str
    expected: str
    error_words: list[str] = field(default_factory=list)
    notes: str = ""


DYSLEXIC_TEST_SAMPLES: list[TestSample] = [
    # === LETTER REVERSALS (b/d, p/q, m/w, n/u) ===
    TestSample(
        category="letter_reversal",
        input_text="The dog dug a big hole in the dack yard.",
        expected="The dog dug a big hole in the back yard.",
        error_words=["dack"],
        notes="b->d reversal in 'back'",
    ),
    TestSample(
        category="letter_reversal",
        input_text="She bought a new bed for her daby.",
        expected="She bought a new bed for her baby.",
        error_words=["daby"],
        notes="b->d reversal in 'baby'",
    ),
    TestSample(
        category="letter_reversal",
        input_text="He rode his dike to school every morning.",
        expected="He rode his bike to school every morning.",
        error_words=["dike"],
        notes="b->d reversal in 'bike'",
    ),
    TestSample(
        category="letter_reversal",
        input_text="Please be puiet during the test.",
        expected="Please be quiet during the test.",
        error_words=["puiet"],
        notes="q->p reversal in 'quiet'",
    ),
    TestSample(
        category="letter_reversal",
        input_text="The quipment needs to be replaced soon.",
        expected="The equipment needs to be replaced soon.",
        error_words=["quipment"],
        notes="e->q substitution in 'equipment'",
    ),
    TestSample(
        category="letter_reversal",
        input_text="I saw a wouse run across the kitchen floor.",
        expected="I saw a mouse run across the kitchen floor.",
        error_words=["wouse"],
        notes="m->w reversal in 'mouse'",
    ),
    TestSample(
        category="letter_reversal",
        input_text="The uew student joined our class today.",
        expected="The new student joined our class today.",
        error_words=["uew"],
        notes="n->u reversal in 'new'",
    ),

    # === TRANSPOSITIONS (adjacent letter swaps) ===
    TestSample(
        category="transposition",
        input_text="Teh cat sat on teh mat and looked out teh window.",
        expected="The cat sat on the mat and looked out the window.",
        error_words=["Teh", "teh", "teh"],
        notes="Classic 'teh' -> 'the' (most common dyslexic transposition)",
    ),
    TestSample(
        category="transposition",
        input_text="I liek to play wiht my friends adn ride bikes.",
        expected="I like to play with my friends and ride bikes.",
        error_words=["liek", "wiht", "adn"],
        notes="Multiple common transpositions",
    ),
    TestSample(
        category="transposition",
        input_text="She jsut came bakc form the store.",
        expected="She just came back from the store.",
        error_words=["jsut", "bakc", "form"],
        notes="Multiple transpositions in one sentence",
    ),
    TestSample(
        category="transposition",
        input_text="Thier team won becuase they practiced every day.",
        expected="Their team won because they practiced every day.",
        error_words=["Thier", "becuase"],
        notes="Common 'their/because' transpositions",
    ),
    TestSample(
        category="transposition",
        input_text="Waht si teh porbelm with tihs computer?",
        expected="What is the problem with this computer?",
        error_words=["Waht", "si", "teh", "porbelm", "tihs"],
        notes="Heavy transpositions throughout",
    ),

    # === PHONETIC SUBSTITUTIONS (writing how it sounds) ===
    TestSample(
        category="phonetic",
        input_text="I had enuff food for dinner last nite.",
        expected="I had enough food for dinner last night.",
        error_words=["enuff", "nite"],
        notes="Phonetic: 'enough' -> 'enuff', 'night' -> 'nite'",
    ),
    TestSample(
        category="phonetic",
        input_text="The fone rang wile I was in the shower.",
        expected="The phone rang while I was in the shower.",
        error_words=["fone", "wile"],
        notes="ph->f substitution, silent letters dropped",
    ),
    TestSample(
        category="phonetic",
        input_text="He brot his frend to the skool dance.",
        expected="He brought his friend to the school dance.",
        error_words=["brot", "frend", "skool"],
        notes="Phonetic spelling of brought/friend/school",
    ),
    TestSample(
        category="phonetic",
        input_text="She sed she wood come to the partee.",
        expected="She said she would come to the party.",
        error_words=["sed", "wood", "partee"],
        notes="Phonetic: said->sed, would->wood, party->partee",
    ),
    TestSample(
        category="phonetic",
        input_text="The docter told me to take the medisine every morning.",
        expected="The doctor told me to take the medicine every morning.",
        error_words=["docter", "medisine"],
        notes="Common phonetic variants",
    ),
    TestSample(
        category="phonetic",
        input_text="I want to lern how to rite better essayes.",
        expected="I want to learn how to write better essays.",
        error_words=["lern", "rite", "essayes"],
        notes="Phonetic: learn/write/essays",
    ),

    # === OMISSIONS (missing letters) ===
    TestSample(
        category="omission",
        input_text="He went to the libary to get a new bok.",
        expected="He went to the library to get a new book.",
        error_words=["libary", "bok"],
        notes="Missing 'r' in library, missing 'o' in book",
    ),
    TestSample(
        category="omission",
        input_text="The goverment announced new rules for the enviroment.",
        expected="The government announced new rules for the environment.",
        error_words=["goverment", "enviroment"],
        notes="Missing 'n' in government, missing 'n' in environment",
    ),
    TestSample(
        category="omission",
        input_text="She recieved a beautful present for her brithday.",
        expected="She received a beautiful present for her birthday.",
        error_words=["recieved", "beautful", "brithday"],
        notes="Missing/swapped letters in common words",
    ),
    TestSample(
        category="omission",
        input_text="The resturant had excelent food and frendly service.",
        expected="The restaurant had excellent food and friendly service.",
        error_words=["resturant", "excelent", "frendly"],
        notes="Dropped vowels in longer words",
    ),
    TestSample(
        category="omission",
        input_text="I probly should of studed more for the exm.",
        expected="I probably should have studied more for the exam.",
        error_words=["probly", "of", "studed", "exm"],
        notes="Heavy omissions throughout",
    ),

    # === HOMOPHONE CONFUSION ===
    TestSample(
        category="homophone",
        input_text="There going to the store with they're bags.",
        expected="They're going to the store with their bags.",
        error_words=["There", "they're"],
        notes="there/their/they're confusion",
    ),
    TestSample(
        category="homophone",
        input_text="I want to by a peace of cake for desert.",
        expected="I want to buy a piece of cake for dessert.",
        error_words=["by", "peace", "desert"],
        notes="buy/by, piece/peace, dessert/desert",
    ),
    TestSample(
        category="homophone",
        input_text="The whether outside was to cold for a walk.",
        expected="The weather outside was too cold for a walk.",
        error_words=["whether", "to"],
        notes="weather/whether, too/to",
    ),
    TestSample(
        category="homophone",
        input_text="I herd that the knew teacher is really nice.",
        expected="I heard that the new teacher is really nice.",
        error_words=["herd", "knew"],
        notes="heard/herd, new/knew",
    ),

    # === INSERTIONS (extra letters) ===
    TestSample(
        category="insertion",
        input_text="She finallly finished her homeworkk last nightt.",
        expected="She finally finished her homework last night.",
        error_words=["finallly", "homeworkk", "nightt"],
        notes="Doubled consonants",
    ),
    TestSample(
        category="insertion",
        input_text="The chilldren playeed in the parke after lunnch.",
        expected="The children played in the park after lunch.",
        error_words=["chilldren", "playeed", "parke", "lunnch"],
        notes="Extra letters inserted throughout",
    ),

    # === MIXED / SEVERE (multiple error types in one sentence) ===
    TestSample(
        category="mixed_severe",
        input_text="I dint no wat teh teecher sed becuz I wasnt lisening.",
        expected="I didn't know what the teacher said because I wasn't listening.",
        error_words=["dint", "no", "wat", "teh", "teecher", "sed", "becuz", "wasnt", "lisening"],
        notes="Multiple error types: omission, phonetic, transposition",
    ),
    TestSample(
        category="mixed_severe",
        input_text="My favrit suject is sience becuse we do expirements.",
        expected="My favorite subject is science because we do experiments.",
        error_words=["favrit", "suject", "sience", "becuse", "expirements"],
        notes="Phonetic + omission across the sentence",
    ),
    TestSample(
        category="mixed_severe",
        input_text="Teh importent thing is too nevr give up on yuor dreems.",
        expected="The important thing is to never give up on your dreams.",
        error_words=["Teh", "importent", "too", "nevr", "yuor", "dreems"],
        notes="Transposition + spelling + homophone + reversal",
    ),
    TestSample(
        category="mixed_severe",
        input_text="I woud liek too go too teh park becuase its a butiful day.",
        expected="I would like to go to the park because it's a beautiful day.",
        error_words=["woud", "liek", "too", "too", "teh", "becuase", "its", "butiful"],
        notes="Very heavy error density — realistic severe dyslexic writing",
    ),
    TestSample(
        category="mixed_severe",
        input_text="Yesturday I tryed to rite a storey abowt my faimly but it waz realy hard.",
        expected="Yesterday I tried to write a story about my family but it was really hard.",
        error_words=["Yesturday", "tryed", "rite", "storey", "abowt", "faimly", "waz", "realy"],
        notes="Realistic dyslexic journal entry",
    ),
    TestSample(
        category="mixed_severe",
        input_text="Wen I gro up I whant to bee a docter and hlep pepole.",
        expected="When I grow up I want to be a doctor and help people.",
        error_words=["Wen", "gro", "whant", "bee", "docter", "hlep", "pepole"],
        notes="Child with dyslexia writing sample",
    ),

    # === CLEAN TEXT (no errors — tests false positive rate) ===
    TestSample(
        category="clean",
        input_text="The children played happily in the park after school.",
        expected="The children played happily in the park after school.",
        notes="Clean sentence — should produce zero corrections",
    ),
    TestSample(
        category="clean",
        input_text="Scientists discovered a new species of butterfly in the rainforest.",
        expected="Scientists discovered a new species of butterfly in the rainforest.",
        notes="Clean sentence with longer words",
    ),
    TestSample(
        category="clean",
        input_text="The orchestra performed a beautiful symphony at the concert hall last evening.",
        expected="The orchestra performed a beautiful symphony at the concert hall last evening.",
        notes="Clean complex sentence",
    ),
    TestSample(
        category="clean",
        input_text="She carefully arranged the flowers in the vase on the dining table.",
        expected="She carefully arranged the flowers in the vase on the dining table.",
        notes="Clean sentence — another false-positive check",
    ),
]


def word_error_rate(hypothesis: str, reference: str) -> float:
    """Compute WER between two strings."""
    h_words = hypothesis.strip().split()
    r_words = reference.strip().split()
    if not r_words:
        return 0.0 if not h_words else 1.0

    d = [[0] * (len(r_words) + 1) for _ in range(len(h_words) + 1)]
    for i in range(len(h_words) + 1):
        d[i][0] = i
    for j in range(len(r_words) + 1):
        d[0][j] = j
    for i in range(1, len(h_words) + 1):
        for j in range(1, len(r_words) + 1):
            if h_words[i - 1] == r_words[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + 1)
    return d[len(h_words)][len(r_words)] / len(r_words)


def char_error_rate(hypothesis: str, reference: str) -> float:
    """Compute CER between two strings."""
    h = list(hypothesis.strip())
    r = list(reference.strip())
    if not r:
        return 0.0 if not h else 1.0

    d = [[0] * (len(r) + 1) for _ in range(len(h) + 1)]
    for i in range(len(h) + 1):
        d[i][0] = i
    for j in range(len(r) + 1):
        d[0][j] = j
    for i in range(1, len(h) + 1):
        for j in range(1, len(r) + 1):
            if h[i - 1] == r[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + 1)
    return d[len(h)][len(r)] / len(r)


def errors_fixed_count(input_text: str, output_text: str, expected: str) -> tuple[int, int]:
    """Count how many error words were fixed out of total error words.

    Returns (fixed_count, total_error_words) based on word-level diff.
    """
    in_words = input_text.strip().split()
    out_words = output_text.strip().split()
    exp_words = expected.strip().split()

    # Align by shortest length
    n = min(len(in_words), len(out_words), len(exp_words))
    total_errors = 0
    fixed = 0
    for i in range(n):
        if in_words[i].lower() != exp_words[i].lower():
            total_errors += 1
            if out_words[i].lower() == exp_words[i].lower():
                fixed += 1
    return fixed, total_errors


# -------------------------------------------------------------------------
# Seq2Seq model runner
# -------------------------------------------------------------------------

def run_seq2seq_tests(samples: list[TestSample], verbose: bool = False) -> dict[str, Any]:
    """Run all test samples through the seq2seq model."""
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    logger.info(f"\n  Loading seq2seq model from {SEQ2SEQ_MODEL_DIR}...")
    tokenizer = AutoTokenizer.from_pretrained(str(SEQ2SEQ_MODEL_DIR))
    model = AutoModelForSeq2SeqLM.from_pretrained(str(SEQ2SEQ_MODEL_DIR))
    model.eval()
    logger.info("  Model loaded.")

    # Warmup
    for _ in range(3):
        inputs = tokenizer("correct: teh cat sat on teh mat", return_tensors="pt", truncation=True, max_length=128)
        with torch.no_grad():
            model.generate(**inputs, max_length=128, num_beams=1)

    results_by_category: dict[str, list[dict]] = {}
    all_results: list[dict] = []

    for sample in samples:
        prompt = f"correct: {sample.input_text}"
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=128)

        start = time.perf_counter()
        with torch.no_grad():
            outputs = model.generate(**inputs, max_length=128, num_beams=1)
        latency_ms = (time.perf_counter() - start) * 1000

        prediction = tokenizer.decode(outputs[0], skip_special_tokens=True)
        exact_match = prediction.strip() == sample.expected.strip()
        wer = word_error_rate(prediction, sample.expected)
        cer = char_error_rate(prediction, sample.expected)
        fixed, total_errs = errors_fixed_count(sample.input_text, prediction, sample.expected)

        result = {
            "category": sample.category,
            "input": sample.input_text,
            "expected": sample.expected,
            "prediction": prediction,
            "exact_match": exact_match,
            "wer": wer,
            "cer": cer,
            "errors_fixed": fixed,
            "total_errors": total_errs,
            "latency_ms": latency_ms,
            "notes": sample.notes,
        }
        all_results.append(result)

        if sample.category not in results_by_category:
            results_by_category[sample.category] = []
        results_by_category[sample.category].append(result)

    return {"all": all_results, "by_category": results_by_category}


# -------------------------------------------------------------------------
# ONNX token-classification model runner
# -------------------------------------------------------------------------

def run_onnx_tests(samples: list[TestSample], verbose: bool = False) -> dict[str, Any]:
    """Run all test samples through the ONNX token-classification model."""
    import onnxruntime as ort
    from transformers import AutoTokenizer

    onnx_file = ONNX_MODEL_DIR / "model.onnx"
    logger.info(f"\n  Loading ONNX model from {onnx_file}...")
    tokenizer = AutoTokenizer.from_pretrained(str(ONNX_MODEL_DIR))
    session = ort.InferenceSession(str(onnx_file), providers=["CPUExecutionProvider"])
    logger.info("  ONNX model loaded.")

    # Warmup
    for _ in range(5):
        tok = tokenizer("teh cat sat on teh mat", return_tensors="np", truncation=True, padding=True, max_length=128)
        feed = {"input_ids": tok["input_ids"].astype(np.int64), "attention_mask": tok["attention_mask"].astype(np.int64)}
        session.run(None, feed)

    results_by_category: dict[str, list[dict]] = {}
    all_results: list[dict] = []

    for sample in samples:
        tok = tokenizer(
            sample.input_text, return_tensors="np", truncation=True, padding=True, max_length=128
        )
        feed = {
            "input_ids": tok["input_ids"].astype(np.int64),
            "attention_mask": tok["attention_mask"].astype(np.int64),
        }

        start = time.perf_counter()
        outputs = session.run(None, feed)
        latency_ms = (time.perf_counter() - start) * 1000

        predictions = np.argmax(outputs[0], axis=-1)[0]
        word_ids = tok.word_ids(batch_index=0)

        words = sample.input_text.split()
        word_preds = [0] * len(words)
        seen: set[int] = set()
        for token_idx, word_id in enumerate(word_ids):
            if word_id is not None and word_id not in seen:
                if word_id < len(word_preds):
                    word_preds[word_id] = int(predictions[token_idx])
                seen.add(word_id)

        # Count errors detected
        detected_error_words = [words[i] for i in range(len(words)) if i < len(word_preds) and word_preds[i] != 0]

        # For error samples, how many real errors were detected?
        expected_words = sample.expected.split()
        true_errors = []
        for i in range(min(len(words), len(expected_words))):
            if words[i].lower() != expected_words[i].lower():
                true_errors.append(i)

        detected_true = sum(1 for i in true_errors if i < len(word_preds) and word_preds[i] != 0)
        # False positives on clean words
        clean_indices = [i for i in range(min(len(words), len(expected_words))) if words[i].lower() == expected_words[i].lower()]
        false_positives = sum(1 for i in clean_indices if i < len(word_preds) and word_preds[i] != 0)

        result = {
            "category": sample.category,
            "input": sample.input_text,
            "expected": sample.expected,
            "word_labels": word_preds,
            "detected_error_words": detected_error_words,
            "true_errors": len(true_errors),
            "detected_true_errors": detected_true,
            "false_positives": false_positives,
            "recall": detected_true / len(true_errors) if true_errors else 1.0,
            "precision": detected_true / (detected_true + false_positives) if (detected_true + false_positives) > 0 else 1.0,
            "latency_ms": latency_ms,
            "notes": sample.notes,
        }
        all_results.append(result)

        if sample.category not in results_by_category:
            results_by_category[sample.category] = []
        results_by_category[sample.category].append(result)

    return {"all": all_results, "by_category": results_by_category}


# -------------------------------------------------------------------------
# Reporting
# -------------------------------------------------------------------------

def print_seq2seq_report(data: dict[str, Any], verbose: bool = False) -> None:
    """Print seq2seq test results."""
    logger.info("\n" + "=" * 78)
    logger.info("  SEQ2SEQ MODEL (T5-small) — Dyslexic Writing Test Results")
    logger.info("=" * 78)

    all_results = data["all"]
    by_cat = data["by_category"]

    # Per-category table
    logger.info(f"\n  {'Category':<20} {'Samples':>7} {'Exact':>7} {'EM%':>7} {'Avg WER':>9} {'Avg CER':>9} {'Fixed':>7} {'Errs':>6} {'Fix%':>7} {'Avg ms':>8}")
    logger.info("  " + "-" * 96)

    for cat in ["letter_reversal", "transposition", "phonetic", "omission", "homophone", "insertion", "mixed_severe", "clean"]:
        if cat not in by_cat:
            continue
        results = by_cat[cat]
        n = len(results)
        exact = sum(1 for r in results if r["exact_match"])
        avg_wer = np.mean([r["wer"] for r in results])
        avg_cer = np.mean([r["cer"] for r in results])
        total_fixed = sum(r["errors_fixed"] for r in results)
        total_errs = sum(r["total_errors"] for r in results)
        fix_pct = (total_fixed / total_errs * 100) if total_errs > 0 else 100.0
        avg_lat = np.mean([r["latency_ms"] for r in results])

        logger.info(
            f"  {cat:<20} {n:>7} {exact:>7} {exact/n*100:>6.1f}% {avg_wer:>9.4f} {avg_cer:>9.4f} "
            f"{total_fixed:>5}/{total_errs:<3} {fix_pct:>6.1f}% {avg_lat:>7.1f}"
        )

    # Overall
    n = len(all_results)
    exact = sum(1 for r in all_results if r["exact_match"])
    avg_wer = np.mean([r["wer"] for r in all_results])
    avg_cer = np.mean([r["cer"] for r in all_results])
    total_fixed = sum(r["errors_fixed"] for r in all_results)
    total_errs = sum(r["total_errors"] for r in all_results)
    fix_pct = (total_fixed / total_errs * 100) if total_errs > 0 else 100.0
    avg_lat = np.mean([r["latency_ms"] for r in all_results])
    latencies = [r["latency_ms"] for r in all_results]

    logger.info("  " + "-" * 96)
    logger.info(
        f"  {'OVERALL':<20} {n:>7} {exact:>7} {exact/n*100:>6.1f}% {avg_wer:>9.4f} {avg_cer:>9.4f} "
        f"{total_fixed:>5}/{total_errs:<3} {fix_pct:>6.1f}% {avg_lat:>7.1f}"
    )

    logger.info(f"\n  Latency: avg={avg_lat:.1f}ms  p50={np.percentile(latencies, 50):.1f}ms  "
                f"p95={np.percentile(latencies, 95):.1f}ms  min={min(latencies):.1f}ms  max={max(latencies):.1f}ms")

    # False positives on clean text
    clean = by_cat.get("clean", [])
    if clean:
        fp_count = sum(1 for r in clean if not r["exact_match"])
        logger.info(f"\n  False positives on clean text: {fp_count}/{len(clean)} sentences modified (should be 0)")

    if verbose:
        logger.info("\n  --- Sample-Level Details ---")
        for r in all_results:
            status = "PASS" if r["exact_match"] else "MISS"
            logger.info(f"\n  [{status}] {r['category']} | {r['notes']}")
            logger.info(f"    Input:    {r['input']}")
            logger.info(f"    Expected: {r['expected']}")
            logger.info(f"    Got:      {r['prediction']}")
            if not r["exact_match"]:
                logger.info(f"    WER: {r['wer']:.4f}  CER: {r['cer']:.4f}  Fixed: {r['errors_fixed']}/{r['total_errors']}")


def print_onnx_report(data: dict[str, Any], verbose: bool = False) -> None:
    """Print ONNX token-classification test results."""
    logger.info("\n" + "=" * 78)
    logger.info("  ONNX TOKEN CLASSIFICATION MODEL — Dyslexic Writing Test Results")
    logger.info("=" * 78)

    all_results = data["all"]
    by_cat = data["by_category"]

    logger.info(f"\n  {'Category':<20} {'Samples':>7} {'TrueErr':>7} {'Detect':>7} {'Recall':>8} {'FP':>5} {'Precis':>8} {'Avg ms':>8}")
    logger.info("  " + "-" * 78)

    for cat in ["letter_reversal", "transposition", "phonetic", "omission", "homophone", "insertion", "mixed_severe", "clean"]:
        if cat not in by_cat:
            continue
        results = by_cat[cat]
        n = len(results)
        total_true = sum(r["true_errors"] for r in results)
        total_detected = sum(r["detected_true_errors"] for r in results)
        total_fp = sum(r["false_positives"] for r in results)
        recall = total_detected / total_true if total_true > 0 else 1.0
        precision = total_detected / (total_detected + total_fp) if (total_detected + total_fp) > 0 else 1.0
        avg_lat = np.mean([r["latency_ms"] for r in results])

        logger.info(
            f"  {cat:<20} {n:>7} {total_true:>7} {total_detected:>7} {recall:>7.1%} {total_fp:>5} {precision:>7.1%} {avg_lat:>7.2f}"
        )

    # Overall
    n = len(all_results)
    total_true = sum(r["true_errors"] for r in all_results)
    total_detected = sum(r["detected_true_errors"] for r in all_results)
    total_fp = sum(r["false_positives"] for r in all_results)
    recall = total_detected / total_true if total_true > 0 else 1.0
    precision = total_detected / (total_detected + total_fp) if (total_detected + total_fp) > 0 else 1.0
    avg_lat = np.mean([r["latency_ms"] for r in all_results])
    latencies = [r["latency_ms"] for r in all_results]

    logger.info("  " + "-" * 78)
    logger.info(
        f"  {'OVERALL':<20} {n:>7} {total_true:>7} {total_detected:>7} {recall:>7.1%} {total_fp:>5} {precision:>7.1%} {avg_lat:>7.2f}"
    )

    logger.info(f"\n  Latency: avg={avg_lat:.2f}ms  p50={np.percentile(latencies, 50):.2f}ms  "
                f"p95={np.percentile(latencies, 95):.2f}ms  min={min(latencies):.2f}ms  max={max(latencies):.2f}ms")

    clean = by_cat.get("clean", [])
    if clean:
        total_clean_fp = sum(r["false_positives"] for r in clean)
        total_clean_words = sum(len(r["input"].split()) for r in clean)
        logger.info(f"\n  False positives on clean text: {total_clean_fp}/{total_clean_words} words flagged (should be 0)")

    if verbose:
        logger.info("\n  --- Sample-Level Details ---")
        for r in all_results:
            status = "OK" if r["true_errors"] == 0 or r["detected_true_errors"] > 0 else "MISS"
            logger.info(f"\n  [{status}] {r['category']} | {r['notes']}")
            logger.info(f"    Input:    {r['input']}")
            logger.info(f"    Detected: {r['detected_error_words']}")
            logger.info(f"    Recall: {r['recall']:.1%}  Precision: {r['precision']:.1%}  FP: {r['false_positives']}  Latency: {r['latency_ms']:.2f}ms")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Test models on dyslexic writing samples")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print sample-level details")
    parser.add_argument("--seq2seq-only", action="store_true", help="Only test seq2seq model")
    parser.add_argument("--onnx-only", action="store_true", help="Only test ONNX model")
    parser.add_argument("--output", type=str, default=None, help="Path to save JSON results")
    args = parser.parse_args()

    logger.info("=" * 78)
    logger.info("  DysLex AI — Dyslexic Writing Test Suite")
    logger.info(f"  {len(DYSLEXIC_TEST_SAMPLES)} hand-crafted samples across {len(set(s.category for s in DYSLEXIC_TEST_SAMPLES))} categories")
    logger.info("=" * 78)

    report: dict[str, Any] = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    run_both = not args.seq2seq_only and not args.onnx_only

    # Seq2seq tests
    if not args.onnx_only:
        if SEQ2SEQ_MODEL_DIR.exists():
            seq2seq_data = run_seq2seq_tests(DYSLEXIC_TEST_SAMPLES, verbose=args.verbose)
            print_seq2seq_report(seq2seq_data, verbose=args.verbose)
            report["seq2seq"] = seq2seq_data["all"]
        else:
            logger.info(f"\n  Seq2seq model not found at {SEQ2SEQ_MODEL_DIR} — skipping")

    # ONNX tests
    if not args.seq2seq_only:
        onnx_file = ONNX_MODEL_DIR / "model.onnx"
        if onnx_file.exists():
            onnx_data = run_onnx_tests(DYSLEXIC_TEST_SAMPLES, verbose=args.verbose)
            print_onnx_report(onnx_data, verbose=args.verbose)
            report["onnx"] = onnx_data["all"]
        else:
            logger.info(f"\n  ONNX model not found at {onnx_file} — skipping")

    # Save report
    output_path = Path(args.output) if args.output else SEQ2SEQ_MODEL_DIR / "dyslexic_test_report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info(f"\n  Report saved to {output_path}")

    logger.info("\n" + "=" * 78)
    logger.info("  Test complete.")
    logger.info("=" * 78)


if __name__ == "__main__":
    main()
