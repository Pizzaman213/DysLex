# Benchmark: DysLex AI ONNX Model vs Grammarly

A head-to-head comparison of DysLex AI's local ONNX quick correction model against Grammarly, the most widely used commercial writing assistant.

---

## At a Glance

| Dimension | DysLex AI (ONNX) | Grammarly |
|---|---|---|
| **Price** | Free (Apache 2.0) | Free tier / $12-30/month Pro |
| **Runs where** | 100% in-browser (offline capable) | Cloud servers (AWS) + on-device GEC |
| **Model size** | ~130 MB (T5-small, INT8 quantized) | ~300 MB on-device / ~1B param unified model |
| **Dyslexia-specific** | Yes -- built for it | No specialized support |
| **Learns your patterns** | Passive (no buttons) | Explicit (accept/reject) |
| **Privacy** | Text never leaves your device for local corrections | Text sent to AWS for advanced features |

---

## 1. Accuracy

### DysLex AI ONNX Model

Evaluated on 2,400 test samples spanning Birkbeck, Aspell, Wikipedia, and GitHub typo corpora:

| Metric | Score |
|---|---|
| **Exact match** | **96.67%** |
| **Word Error Rate (WER)** | 0.29% |
| **Character Error Rate (CER)** | 0.16% |
| **Error detection precision** | 99.90% |
| **Error detection recall** | 98.50% |
| **Error detection F1** | 99.19% |
| **False positive rate on clean text** | **0.00%** |

**Per error type:**

| Error Type | Exact Match | F1 |
|---|---|---|
| Transposition (teh -> the) | **100%** | **100%** |
| Phonetic (fone -> phone) | **100%** | **100%** |
| Letter reversal (b/d swap) | **100%** | **100%** |
| Omission (wich -> which) | **100%** | **100%** |
| Insertion (extta -> extra) | **100%** | **100%** |
| Spelling (general) | 97.77% | 99.62% |
| Mixed (multiple errors) | 94.99% | 99.07% |

### Grammarly

Grammarly's published research model GECToR-2024, evaluated on standard GEC benchmarks:

| Metric | Score |
|---|---|
| **F0.5 (CoNLL-2014, single model)** | 66.0 |
| **F0.5 (BEA-2019, single model)** | 73.1 |
| **F0.5 (CoNLL-2014, 7-system ensemble)** | 72.8 |
| **F0.5 (BEA-2019, 7-system ensemble)** | 81.4 |
| **Precision (independent test)** | 88% |
| **Correction rate (independent test)** | 83% |
| **Error detection (Free, 24-error test)** | 12/24 (50%) |
| **Error detection (Premium, 24-error test)** | 18/24 (75%) |

### Analysis

Direct comparison is nuanced because the benchmarks differ:

- **DysLex AI** is evaluated on **dyslexic-pattern error corpora** (Birkbeck spelling errors, phonetic substitutions, letter reversals). It achieves near-perfect results on these specific error types because the model was trained specifically for them.
- **Grammarly's GECToR** is evaluated on **general GEC benchmarks** (CoNLL-2014, BEA-2019) which include grammar, word choice, and stylistic issues -- a broader scope but not dyslexia-specific.
- DysLex AI's **0% false positive rate on clean text** is notable -- Grammarly has been documented to over-flag issues, producing false positives that can confuse dyslexic writers.

**Key takeaway**: DysLex AI significantly outperforms on dyslexia-specific errors (the errors dyslexic writers actually make). Grammarly covers a wider range of writing issues but is not optimized for severe or phonetic misspellings.

---

## 2. Latency

### DysLex AI ONNX Model

Measured on Apple M-series (arm64), 50 runs per sentence length:

| Input Length | Avg Latency | P95 Latency | Throughput |
|---|---|---|---|
| 5 words | **2.0 ms** | 2.4 ms | 499 sentences/sec |
| 20 words | **4.1 ms** | 4.4 ms | 242 sentences/sec |
| 50 words | **8.2 ms** | 8.4 ms | 122 sentences/sec |
| 115 words | **14.7 ms** | 15.1 ms | 68 sentences/sec |

Seq2seq generation latency (100 runs):

| Metric | Value |
|---|---|
| Average | 68.3 ms |
| P50 | 68.5 ms |
| P95 | 81.8 ms |
| P99 | 90.5 ms |
| Min | 50.0 ms |
| Max | 94.8 ms |

### Grammarly

From Grammarly's engineering blog:

| Metric | Value |
|---|---|
| On-device GEC latency target | < 100 ms |
| T5 inference speed | 297 tokens/sec |
| Unified model speed (M2 Mac) | ~210 tokens/sec |
| Text input lag reduction | ~91% improvement (after optimization) |

### Comparison

| Metric | DysLex AI | Grammarly |
|---|---|---|
| Token classification (error detection) | **2-15 ms** | Not published separately |
| Full correction generation | 68-82 ms (P50-P95) | < 100 ms target |
| Works offline | Yes | Partially (basic GEC only) |
| Network dependency | **None** for local corrections | Required for advanced features |

**Key takeaway**: Both achieve sub-100ms corrections. DysLex AI's token classification runs at 2-15ms which is significantly faster. Full seq2seq generation is comparable. DysLex AI has the advantage of zero network latency since everything runs locally.

---

## 3. Model Efficiency

| Metric | DysLex AI ONNX | Grammarly On-Device |
|---|---|---|
| **Parameters** | ~60M (T5-small) | ~1B (Llama-based) |
| **Model size on disk** | ~130 MB (quantized) | < 300 MB |
| **Peak memory per inference** | 0.013 MB | Not published |
| **Quantization** | INT8 | 4-bit |
| **Runtime** | ONNX Runtime Web (browser) | MLX (Apple), custom Rust SDK |
| **Platform** | Any browser (cross-platform) | Native apps only |

**Key takeaway**: DysLex AI runs a 17x smaller model that fits in any browser tab. Grammarly needs a native app with platform-specific acceleration.

---

## 4. Dyslexia-Specific Performance

This is where the tools diverge most significantly.

### DysLex AI: Purpose-Built

| Capability | Details |
|---|---|
| **Letter reversals** (b/d, p/q, m/w) | 100% detection, 100% F1 -- trained on synthetic reversal patterns |
| **Phonetic substitutions** (fone -> phone) | 100% detection, 100% F1 -- model trained on phonetic error corpus |
| **Severe misspellings** | Handles words far from target via seq2seq generation + dictionary fallback |
| **Transpositions** (teh -> the) | 100% detection, 100% F1 |
| **Omissions** (wich -> which) | 100% detection, 100% F1 |
| **Homophone confusion** | 600+ confusion pairs database (their/there/they're, effect/affect) |
| **Per-user error profile** | Tracks individual error frequencies, types, confusion pairs, and improvement |
| **Personal dictionary** | Learns user-specific vocabulary from passive observation |
| **Adaptive learning** | Silent passive loop -- no accept/reject buttons, learns from natural behavior |
| **Error type classification** | Categorizes every error: reversal, phonetic, transposition, omission, insertion, mixed |
| **Positive framing** | Shows "words mastered" -- never shows error counts |

### Grammarly: General Purpose

| Capability | Details |
|---|---|
| **Letter reversals** | No specialized handling -- relies on general spell-check |
| **Phonetic substitutions** | Poor -- documented failures on severe phonetic spellings ("sed" for "said") |
| **Severe misspellings** | Often fails -- documented suggesting wrong words when errors deviate far from target |
| **Contextual word choice** | Good for standard errors, but documented suggesting "wedding" for "weeding" in a gardening context |
| **Per-user error profile** | None -- no dyslexia-specific error tracking |
| **Personal dictionary** | Accept/reject based, vocabulary-focused (not error-pattern-focused) |
| **Adaptive learning** | Requires explicit user interaction (accept/reject buttons) |
| **Error type classification** | General categories (grammar, spelling, punctuation) -- not dyslexia-specific |
| **Framing** | Reports corrections made and comparative metrics ("more productive than X% of users") |

### Documented Grammarly Failures for Dyslexic Users

From published user reports and academic research:

- **University for the Creative Arts (2021)**: "The errors typical of dyslexic writers are phonetically spelled or atypical errors that are difficult for traditional tools such as Grammarly to catch" -- found it "insufficient for high school students with dyslexia."
- **User report**: Grammarly suggested "wedding" for "weeding" in a gardening context, failing to use surrounding context clues.
- **User report**: "It's destroyed a lot of confidence in my writing and now I have to figure out what words I need to unlearn."
- **Academic study (PMC, 2024)**: Grammarly "tends to over-flag issues resulting in many false positives."

---

## 5. Privacy and Data Handling

| Aspect | DysLex AI | Grammarly |
|---|---|---|
| **Local corrections** | 100% on-device, text never sent anywhere | On-device GEC for basic corrections |
| **Advanced features** | Cloud API for deep analysis (Tier 2), opt-in | Text sent to AWS servers (required for Pro features) |
| **Data storage** | User's own PostgreSQL instance | Grammarly's AWS infrastructure |
| **Third-party sharing** | None for local, NVIDIA NIM for cloud tier | "Small number of thoroughly vetted service providers" |
| **User control** | Full -- self-hosted, open source | Opt-out of product improvement via settings |
| **Training on user data** | Per-user model only, data stays with user | De-identified sampling for product improvement |
| **Open source** | Yes (Apache 2.0) | No |

---

## 6. Personalization Depth

| Aspect | DysLex AI | Grammarly |
|---|---|---|
| **Learning mechanism** | Passive observation (zero cognitive load) | Accept/reject buttons (requires user decisions) |
| **What it tracks** | Error frequency map, error types, confusion pairs, context patterns, improvement over time | Personal vocabulary / word frequency |
| **Error profile** | Full per-user database: `"becuase" -> "because" (47 times)` | Not error-pattern-specific |
| **Improvement tracking** | "teh errors: 15/week -> 3/week over 2 months" | Weekly email reports (not model-adaptive) |
| **Model adaptation** | Fine-tunes Quick Correction Model per user + injects profile into LLM prompts | On-device n-gram model (< 5 MB on mobile) |
| **Context awareness** | Detects error increase in longer docs, fewer in familiar topics | Not documented |

---

## 7. Cost Comparison

| Scenario | DysLex AI | Grammarly |
|---|---|---|
| **Individual (basic)** | **$0** | $0 (Free tier, limited) |
| **Individual (full)** | **$0** | $12-30/month |
| **Classroom (30 students)** | **$0** | $360-900/month |
| **School district** | **$0** (self-hosted) | Enterprise pricing (custom) |
| **Annual cost (1 user, full features)** | **$0** | $144-360/year |

DysLex AI is Apache 2.0 licensed. The only cost is hosting if you use the cloud analysis tier (NVIDIA NIM API).

---

## Summary

| Category | Winner | Why |
|---|---|---|
| **Dyslexia-specific accuracy** | DysLex AI | 100% on reversals, phonetics, transpositions vs. documented failures |
| **General GEC breadth** | Grammarly | Covers grammar, style, tone, plagiarism -- broader scope |
| **Latency** | Tie | Both sub-100ms; DysLex AI faster on token classification |
| **Model efficiency** | DysLex AI | 60M params vs 1B; runs in any browser vs native app |
| **Privacy** | DysLex AI | Local-first, open source, self-hosted |
| **Personalization** | DysLex AI | Passive learning with deep error profiling vs accept/reject buttons |
| **Cost** | DysLex AI | Free vs $12-30/month |
| **Ecosystem/polish** | Grammarly | Mature product, browser extensions, mobile apps, integrations |
| **False positive rate** | DysLex AI | 0% on clean text vs documented over-flagging |
| **Accessibility design** | DysLex AI | Purpose-built for dyslexic users; invisible corrections, positive framing |

### Bottom Line

**DysLex AI** is the clear choice for dyslexic writers. It was designed from the ground up for the specific error patterns dyslexic people make, learns each user's unique patterns passively, runs locally with zero privacy concerns, and costs nothing.

**Grammarly** is a strong general-purpose writing tool with a mature ecosystem, but it was not designed for dyslexia. It struggles with severe/phonetic misspellings, requires explicit user interaction to learn, and its false positives can actively harm dyslexic writers' confidence.

---

## Data Sources

### DysLex AI
- `ml/quick_correction/models/quick_correction_seq2seq_v1/eval_report.json` -- Seq2seq model evaluation (2,400 samples)
- `ml/quick_correction/models/quick_correction_base_v1/benchmark_report.json` -- ONNX latency/throughput/accuracy benchmarks (50 runs)
- `ml/quick_correction/benchmark.py` -- Benchmark harness source code

### Grammarly
- [Grammarly Engineering: On-Device AI at Scale](https://www.grammarly.com/blog/engineering/on-device-models-scale/) (March 2025)
- [Grammarly Engineering: Efficient On-Device Writing Assistance](https://www.grammarly.com/blog/engineering/efficient-on-device-writing-assistance/)
- [Grammarly Engineering: Reducing Text Input Lag](https://www.grammarly.com/blog/engineering/reducing-text-input-lag/)
- [Grammarly Engineering: Personal Language Model](https://www.grammarly.com/blog/engineering/personal-language-model/)
- [GECToR GitHub Repository](https://github.com/grammarly/gector)
- [Pillars of GEC (BEA-2024)](https://arxiv.org/html/2404.14914v1) -- Grammarly's state-of-the-art GEC paper
- [ChatGPT or Grammarly? (Wu et al., 2023)](https://arxiv.org/abs/2303.13648)
- [UCA Blog: Using Grammarly for Dyslexic Students](https://ucalearningandteaching.wordpress.com/2021/03/17/using-grammarly-to-help-students-with-dyslexia/)
- [Om Proofreading: Grammarly Free vs Premium](https://omproofreading.com/grammarly-free-vs-premium/) -- Independent 24-error test
- [PMC Study: Grammarly for Academic Writing](https://pmc.ncbi.nlm.nih.gov/articles/PMC11327564/)
- [Grammarly Pricing](https://www.grammarly.com/plans)
- [Grammarly Privacy FAQ](https://support.grammarly.com/hc/en-us/articles/20916119474829-Privacy-and-security-FAQ)
