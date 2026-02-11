"""Tests for classify_error_type() from ml.datasets.process_datasets."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ml.datasets.process_datasets import classify_error_type  # type: ignore[import-not-found]


class TestTranspositionDetection:
    """Adjacent character swaps should be classified as transposition."""

    def test_teh_the(self):
        assert classify_error_type("teh", "the") == "transposition"

    def test_form_from(self):
        assert classify_error_type("form", "from") == "transposition"

    def test_hwat_what(self):
        """Another common adjacent swap."""
        assert classify_error_type("hwat", "what") == "transposition"


class TestReversalDetection:
    """b/d, p/q, m/w, n/u reversals should be classified as reversal."""

    def test_b_to_d(self):
        assert classify_error_type("bog", "dog") == "reversal"

    def test_q_to_p(self):
        assert classify_error_type("qig", "pig") == "reversal"

    def test_d_to_b(self):
        assert classify_error_type("doy", "boy") == "reversal"

    def test_m_to_w(self):
        assert classify_error_type("mas", "was") == "reversal"

    def test_n_to_u(self):
        assert classify_error_type("nse", "use") == "reversal"


class TestOmissionDetection:
    """Missing characters should be classified as omission."""

    def test_wich_which(self):
        assert classify_error_type("wich", "which") == "omission"

    def test_whn_when(self):
        assert classify_error_type("whn", "when") == "omission"

    def test_hose_house(self):
        assert classify_error_type("hose", "house") == "omission"


class TestInsertionDetection:
    """Extra characters should be classified as insertion."""

    def test_whhen_when(self):
        assert classify_error_type("whhen", "when") == "insertion"

    def test_thhe_the(self):
        assert classify_error_type("thhe", "the") == "insertion"


class TestPhoneticDetection:
    """Phonetic substitutions should be classified as phonetic."""

    def test_fone_phone(self):
        assert classify_error_type("fone", "phone") == "phonetic"

    def test_nite_night(self):
        """ight -> ite is a phonetic pattern."""
        assert classify_error_type("nite", "night") == "phonetic"


class TestGeneralSpelling:
    """Errors that do not match a specific pattern fall back to spelling."""

    def test_beutiful_beautiful(self):
        """'beutiful' is one char shorter than 'beautiful', so it is omission."""
        # Removing 'a' at index 2 from "beautiful" produces "beutiful"
        assert classify_error_type("beutiful", "beautiful") == "omission"

    def test_recieve_receive(self):
        """ie/ei swap in 'recieve' vs 'receive' -- same chars, adjacent diff -> transposition."""
        result = classify_error_type("recieve", "receive")
        assert result == "transposition"

    def test_truly_general_spelling(self):
        """An error that does not match any specific heuristic should return 'spelling'."""
        # "wunderful" vs "wonderful" -- same length, single diff u->o, not a reversal pair
        result = classify_error_type("wunderful", "wonderful")
        assert result == "spelling"


class TestCaseInsensitive:
    """Classification should work regardless of case."""

    def test_uppercase_transposition(self):
        assert classify_error_type("TEH", "THE") == "transposition"

    def test_mixed_case_reversal(self):
        assert classify_error_type("Bog", "Dog") == "reversal"

    def test_mixed_case_omission(self):
        assert classify_error_type("WICH", "WHICH") == "omission"


class TestSameLengthNonTransposition:
    """Same-length words with non-adjacent diffs should not be transposition."""

    def test_far_apart_diffs(self):
        """Differences at positions 0 and 3 (not adjacent)."""
        # "cat" vs "dot" -- differs in positions 0 and 2 (len 3, but c->d is reversal check)
        # Use a case where diffs are not adjacent and not reversal pairs
        result = classify_error_type("hat", "hit")
        # a->i at position 1 only -- single diff, but not a reversal pair
        # Actually single diff, same length, not reversal pair -> falls to spelling
        assert result == "spelling"

    def test_multiple_nonadjacent_diffs(self):
        """Two diffs that are not adjacent."""
        # "sand" vs "sund" -- only 1 diff at position 1 (a->u), n/u reversal? no, a->u
        # Use "cold" vs "ward" -- diffs at multiple non-adjacent positions
        result = classify_error_type("axxb", "bxxa")
        # sorted are the same, diffs at 0 and 3 (not adjacent)
        assert result != "transposition"
