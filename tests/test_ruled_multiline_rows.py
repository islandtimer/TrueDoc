"""Lines that pair up across a ruled row's cells are rows of their own."""

from truedoc.tables.ruled import split_multiline_row


def test_paired_lines_become_rows():
    row = ["Cd", "Shapiro W\nP value", "0.46\n< 2.2e-16", "0.15\n< 2.2e-16"]
    assert split_multiline_row(row, 4) == [["Cd", "Shapiro W", "0.46", "0.15"], ["", "P value", "< 2.2e-16", "< 2.2e-16"]]
    spec = ["Medium Resolution Spectrographs (2x)\n# Fibres\nPassband\nVelocity accuracy", "R~5000-7000\n1600 fibres\n390-930 nm\n< 2 km/s"]
    assert split_multiline_row(spec, 2) == [["Medium Resolution Spectrographs (2x)", "R~5000-7000"], ["# Fibres", "1600 fibres"],
                                            ["Passband", "390-930 nm"], ["Velocity accuracy", "< 2 km/s"]]


def test_wrapped_cells_stay_one_row():
    # A wrapped description beside a value and its note.
    assert split_multiline_row(["x", "Superficial partial\nthickness", "2 x 10^6 cells\n(n/a)"], 3) is None
    # A statistic under its value.
    assert split_multiline_row(["a", "0.150**\n(4.07)"], 2) is None
    # A wrapped label with a single value to its right.
    assert split_multiline_row(["Shapiro W\nP value", "0.46"], 2) is None
    # Stacks of different depth.
    assert split_multiline_row(["A\nB\nC", "1\n2"], 2) is None
    # Sentences, not entries.
    assert split_multiline_row(["The quick brown fox jumps over the lazy dog\nAnother sentence follows", "1\n2"], 2) is None
    assert split_multiline_row(["one", "two"], 2) is None
