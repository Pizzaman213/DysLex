# Dyslexic Writing Test Results

Results from testing DysLex AI's two correction models against 39 hand-crafted dyslexic writing samples across 8 error categories. These samples reflect real-world dyslexic writing patterns including letter reversals, transpositions, phonetic substitutions, omissions, homophone confusion, insertions, and severe mixed errors.

Test script: `ml/quick_correction/test_dyslexic.py`

---

## ONNX Token Classification Model (Error Detection)

The ONNX model runs in the browser at ~2.6ms per sentence. Its job is to **detect** which words contain errors.

| Category | Samples | True Errors | Detected | Recall | FP | Precision | Avg Latency |
|---|---|---|---|---|---|---|---|
| Letter reversals | 7 | 7 | 7 | **100%** | 1 | 87.5% | 2.23ms |
| Transpositions | 5 | 16 | 16 | **100%** | 0 | 100% | 2.68ms |
| Phonetic | 6 | 15 | 15 | **100%** | 1 | 93.8% | 2.61ms |
| Omissions | 5 | 14 | 14 | **100%** | 0 | 100% | 2.77ms |
| Homophones | 4 | 9 | 7 | 77.8% | 1 | 87.5% | 2.84ms |
| Insertions | 2 | 7 | 7 | **100%** | 0 | 100% | 2.98ms |
| Mixed/severe | 6 | 43 | 39 | 90.7% | 1 | 97.5% | 3.02ms |
| Clean text | 4 | 0 | 0 | **100%** | **0** | 100% | 2.26ms |
| **OVERALL** | **39** | **111** | **105** | **94.6%** | **4** | **96.3%** | **2.64ms** |

### Detection highlights

- **Zero false positives on clean text** -- all 43 clean words passed through without being flagged
- **100% recall** on letter reversals, transpositions, phonetic errors, omissions, and insertions
- **4 total false positives** across all 39 samples (flagged "our", "I", "The", and "I" as errors when they were correct)
- Homophones are the weakest category (77.8% recall) because detecting them requires sentence-level context, not just spelling checks

### Latency

| Metric | Value |
|---|---|
| Average | 2.64ms |
| P50 | 2.64ms |
| P95 | 3.26ms |
| Min | 1.82ms |
| Max | 3.64ms |

---

## Seq2Seq Model (Error Correction)

The T5-small seq2seq model generates corrected text. Its job is to **fix** the errors, not just detect them.

| Category | Samples | Exact Match | EM% | Avg WER | Avg CER | Errors Fixed | Fix Rate | Avg Latency |
|---|---|---|---|---|---|---|---|---|
| Letter reversals | 7 | 2 | 28.6% | 0.1081 | 0.0949 | 4/7 | 57.1% | 41.8ms |
| Transpositions | 5 | 1 | 20.0% | 0.2736 | 0.2099 | 6/14 | 42.9% | 45.2ms |
| Phonetic | 6 | 3 | 50.0% | 0.1620 | 0.1162 | 9/15 | 60.0% | 44.1ms |
| Omissions | 5 | 3 | 60.0% | 0.1583 | 0.1683 | 9/13 | 69.2% | 42.5ms |
| Homophones | 4 | 0 | 0.0% | 0.1681 | 0.1503 | 4/9 | 44.4% | 45.1ms |
| Insertions | 2 | 1 | 50.0% | 0.0625 | 0.0568 | 6/7 | 85.7% | 38.4ms |
| Mixed/severe | 6 | 0 | 0.0% | 0.4646 | 0.3339 | 7/41 | 17.1% | 56.1ms |
| Clean text | 4 | 4 | 100% | 0.0000 | 0.0000 | N/A | N/A | 56.5ms |
| **OVERALL** | **39** | **14** | **35.9%** | **0.1916** | **0.1531** | **45/106** | **42.5%** | **46.6ms** |

### Correction highlights

- **Zero false positives on clean text** -- all 4 clean sentences passed through unchanged
- **Strong on common single errors**: "teh" -> "the", "libary" -> "library", "goverment" -> "government", "enuff" -> "enough"
- **Insertions** had the best fix rate (85.7%) -- doubled letters are straightforward to remove
- **Omissions** were second best (69.2%) -- missing letters in common words are recoverable
- **Mixed/severe errors** were the weakest (17.1% fix rate) -- when many words are wrong, the model hallucinates different sentences

### Latency

| Metric | Value |
|---|---|
| Average | 46.6ms |
| P50 | 44.6ms |
| P95 | 62.6ms |
| Min | 33.4ms |
| Max | 72.9ms |

---

## Sample-Level Results

### Seq2Seq: What worked

| Input | Output | Category |
|---|---|---|
| Teh cat sat on teh mat and looked out teh window. | The cat sat on the mat and looked out the window. | transposition |
| He rode his dike to school every morning. | He rode his bike to school every morning. | letter_reversal |
| I had enuff food for dinner last nite. | I had enough food for dinner last night. | phonetic |
| The docter told me to take the medisine every morning. | The doctor told me to take the medicine every morning. | phonetic |
| I want to lern how to rite better essayes. | I want to learn how to write better essays. | phonetic |
| He went to the libary to get a new bok. | He went to the library to get a new book. | omission |
| The goverment announced new rules for the enviroment. | The government announced new rules for the environment. | omission |
| She recieved a beautful present for her brithday. | She received a beautiful present for her birthday. | omission |
| She finallly finished her homeworkk last nightt. | She finally finished her homework last night. | insertion |
| The quipment needs to be replaced soon. | The equipment needs to be replaced soon. | letter_reversal |

### Seq2Seq: What failed

| Input | Expected | Got | Problem |
|---|---|---|---|
| She bought a new bed for her daby. | ...her baby. | ...her brother. | Hallucinated a different word |
| Please be puiet during the test. | ...be quiet... | ...be patient... | Wrong word chosen |
| I saw a wouse run across the kitchen floor. | ...a mouse run... | ...a fire running... | Hallucinated completely |
| She jsut came bakc form the store. | She just came back from... | She walked home from... | Rewrote the sentence |
| Waht si teh porbelm with tihs computer? | What is the problem with this computer? | Whehet the computer? | Collapsed under heavy errors |
| She sed she wood come to the partee. | She said she would come to the party. | She sat in the wood to the beach. | Homophone confusion + hallucination |
| I dint no wat teh teecher sed becuz I wasnt lisening. | I didn't know what the teacher said... | I forgot to turn on the desk... | Too many errors, rewrote entirely |
| Wen I gro up I whant to bee a docter and hlep pepole. | When I grow up I want to be a doctor... | I grew up to be a doctor and a child child. | Partial fix then hallucination |

### ONNX: Detection accuracy per sample

All 39 samples were tested. The ONNX model correctly identified errors in every sample. Selected results:

| Input | Errors Detected | Recall |
|---|---|---|
| The dog dug a big hole in the dack yard. | dack | 100% |
| Teh cat sat on teh mat and looked out teh window. | Teh, teh, teh | 100% |
| I liek to play wiht my friends adn ride bikes. | liek, wiht, adn | 100% |
| He brot his frend to the skool dance. | brot, frend, skool | 100% |
| The goverment announced new rules for the enviroment. | goverment, enviroment | 100% |
| She recieved a beautful present for her brithday. | recieved, beautful, brithday | 100% |
| Yesturday I tryed to rite a storey abowt my faimly but it waz realy hard. | Yesturday, tryed, rite, storey, abowt, faimly, waz, realy | 100% |
| I woud liek too go too teh park becuase its a butiful day. | woud, liek, teh, becuase, its, butiful | 75% |
| There going to the store with they're bags. | There, they're | 100% |
| I want to by a peace of cake for desert. | by | 33.3% |

---

## Analysis

### The two-tier architecture is validated

The test results confirm why DysLex AI uses a two-tier correction system:

**Tier 1 (ONNX, in-browser)** excels at error detection. It catches 94.6% of all dyslexic errors at 2.6ms with near-zero false positives. This is the fast gate -- it tells the system *where* the errors are instantly.

**Tier 1 (Seq2Seq, in-browser)** handles simple corrections well -- single common errors like "teh", "libary", "enuff" are fixed reliably at ~47ms. But it breaks down on severe mixed errors and homophones.

**Tier 2 (Nemotron LLM, cloud)** is needed for:
- Severe mixed errors (multiple error types in one sentence)
- Homophones requiring full sentence context
- Cases where the seq2seq model would hallucinate

### Strengths

- **Error detection is production-ready** -- 94.6% recall, 96.3% precision, 2.6ms latency, zero clean-text false positives
- **Common single-error correction works** -- phonetic, omission, insertion, and simple transposition fixes are reliable
- **Both models respect clean text** -- zero false positives means the system won't interrupt writers unnecessarily
- **Latency targets met** -- both models run well under 100ms

### Weaknesses to address

1. **Homophone detection** (77.8% recall) -- the ONNX model misses some homophones because they're real words. The seq2seq model can't resolve them either. Both need Tier 2 for this.

2. **Severe error correction** (17.1% fix rate) -- when 5+ words are wrong in a sentence, the T5-small model hallucinates. It tries to generate a plausible sentence rather than fixing the actual errors. This is expected for a 60M parameter model.

3. **Letter reversal correction** (57.1% fix rate) -- detection is 100%, but the seq2seq sometimes picks the wrong replacement word ("daby" -> "brother" instead of "baby"). The dictionary fallback should catch these.

### Recommendations

1. **Route severe errors to Tier 2** -- if the ONNX detector flags 4+ errors in a sentence, bypass the seq2seq model and send directly to Nemotron for correction.

2. **Use the dictionary for detected reversals** -- since the ONNX model catches 100% of reversals, pair it with the 34K+ entry correction dictionary for replacement instead of relying on seq2seq generation.

3. **Fine-tune on more homophone data** -- both models need more training examples with contextual homophone usage (their/there/they're, to/too/two, by/buy/bye).

4. **Add a confidence threshold** -- when the seq2seq model's output diverges heavily from the input (high edit distance), fall back to dictionary + Tier 2 instead of showing a hallucinated sentence.

---

## Test Environment

- **Platform**: macOS (Apple Silicon arm64)
- **Seq2seq model**: T5-small (~60M params), PyTorch inference
- **ONNX model**: DistilBERT token classification (~66M params), ONNX Runtime
- **Test samples**: 39 hand-crafted sentences across 8 categories
- **Test script**: `ml/quick_correction/test_dyslexic.py`

### Reproducing these results

```bash
# Run full test suite
python ml/quick_correction/test_dyslexic.py

# With sample-level details
python ml/quick_correction/test_dyslexic.py --verbose

# Seq2seq only
python ml/quick_correction/test_dyslexic.py --seq2seq-only

# ONNX only
python ml/quick_correction/test_dyslexic.py --onnx-only

# Save JSON report to custom path
python ml/quick_correction/test_dyslexic.py --output results.json
```
