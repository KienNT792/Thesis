import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import agreement as ag  # noqa: E402

# Krippendorff (2011) worked example: 4 coders, 12 units, missing values.
RAW = {
    "A": [1, 2, 3, 3, 2, 1, 4, 1, 2, None, None, None],
    "B": [1, 2, 3, 3, 2, 2, 4, 1, 2, 5, None, 3],
    "C": [None, 3, 3, 3, 2, 3, 4, 2, 2, 5, 1, None],
    "D": [1, 2, 3, 3, 2, 4, 4, 1, 2, 5, 1, None],
}
UNITS = [[RAW[c][i] for c in RAW if RAW[c][i] is not None] for i in range(12)]


def test_nominal_matches_published():
    assert abs(ag.alpha(UNITS, "nominal") - 0.743) < 0.001


def test_ordinal_matches_published():
    assert abs(ag.alpha(UNITS, "ordinal") - 0.815) < 0.002


def test_interval_matches_published():
    assert abs(ag.alpha(UNITS, "interval") - 0.849) < 0.001


def test_perfect_agreement_is_one():
    assert ag.alpha([[1, 1], [2, 2], [3, 3], [1, 1]], "ordinal") == 1.0


def test_systematic_disagreement_is_low():
    assert ag.alpha([[1, 3], [3, 1], [2, 2], [1, 3], [3, 1]], "ordinal") < 0.2
