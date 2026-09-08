"""A subscript that arrived in two pieces is one subscript.

"E_{s}_{,t}" is not LaTeX at all: two scripts of the same kind in a row, which a renderer
refuses, losing the whole formula (2503.08925 and 2503.08646 in run 62's output). The pieces
belong to one script, as the page shows them: "E_{s,t}".

(The neighbouring spelling question, whether to write the crossed element sign as one command
or two, was settled by measurement in an earlier run and is recorded in `_polish`: the
references favour the two-command form, and rewriting it lost more checks than it won.)
"""
from truedoc.math.reconstruct import _polish

BS = chr(92)


def test_a_script_in_two_pieces_becomes_one():
    assert _polish("(E_{t,s}" + BS + "times E_{s}_{,t})[2]") == "(E_{t,s}" + BS + "times E_{s,t})[2]"
    assert _polish("x^{2}^{a}") == "x^{2a}"


def test_nested_and_ordinary_scripts_are_left_alone():
    assert _polish("x_{a_{b}}") == "x_{a_{b}}"
    assert _polish("x_{a}^{b}") == "x_{a}^{b}"
    assert _polish("y_{i}z_{j}") == "y_{i}z_{j}"
