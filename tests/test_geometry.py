"""TrueDoc's own rectangles and matrices behave exactly as PyMuPDF's, for the operations the product uses
(M18, D007, D022): the product can then drop PyMuPDF's types without a single coordinate moving."""
import math
import random

import pytest

from truedoc.geometry import Matrix, Rect, transform_point


def test_page_rotation_matrices_turn_boxes_as_pymupdf_does():
    """The rotation matrices of the benchmark's turned pages (measured: a 612 x 792 page at 90 degrees
    reads 792 x 612 with matrix (0, 1, -1, 0, 792, 0); at 180, (-1, 0, 0, -1, w, h))."""
    box = Rect(100, 200, 300, 250)
    assert tuple(box * Matrix(0, 1, -1, 0, 792, 0)) == (542.0, 100.0, 592.0, 300.0)
    assert tuple(box * Matrix(-1, 0, 0, -1, 596, 841)) == (296.0, 591.0, 496.0, 641.0)
    back = Rect(542, 100, 592, 300) * ~Matrix(0, 1, -1, 0, 792, 0)
    assert tuple(back.normalize()) == (100.0, 200.0, 300.0, 250.0)


def test_edges_of_an_inverted_or_empty_rect():
    r = Rect(10, 10, 5, 20)
    assert r.width == 0 and r.height == 10 and r.is_empty
    assert tuple(Rect(r).normalize()) == (5.0, 10.0, 10.0, 20.0)
    # PyMuPDF's rule: intersecting with an empty rectangle gives that rectangle
    assert tuple(Rect(0, 0, 10, 10) & Rect(3, 3, 3, 8)) == (3.0, 3.0, 3.0, 8.0)
    # and a union leaves out an empty side
    assert tuple(Rect(0, 0, 10, 10) | Rect(20, 20, 20, 30)) == (0.0, 0.0, 10.0, 10.0)


def test_every_operation_matches_pymupdf_on_random_input():
    pymupdf = pytest.importorskip("pymupdf")
    rng = random.Random(7)
    for _ in range(3000):
        x0, y0 = rng.uniform(-900, 900), rng.uniform(-900, 900)
        r1 = (x0, y0, x0 + rng.uniform(-300, 600), y0 + rng.uniform(-300, 600))
        r2 = (y0, x0, y0 + rng.uniform(-300, 600), x0 + rng.uniform(-300, 600))
        ang, s = rng.uniform(0, 2 * math.pi), rng.uniform(0.2, 3)
        m = rng.choice([(0, 1, -1, 0, rng.uniform(100, 900), 0), (s, 0, 0, s, 3.0, -4.0),
                        (s * math.cos(ang), s * math.sin(ang), -s * math.sin(ang), s * math.cos(ang), 5.0, 7.0)])
        P1, P2, PM = pymupdf.Rect(*r1), pymupdf.Rect(*r2), pymupdf.Matrix(*m)
        D1, D2, DM = Rect(*r1), Rect(*r2), Matrix(*m)
        assert tuple(D1 * DM) == tuple(P1 * PM)
        assert tuple(D1 * PM) == tuple(P1 * PM)
        assert tuple(D1 | D2) == tuple(P1 | P2)
        assert tuple(D1 & D2) == tuple(P1 & P2)
        assert tuple(D1 & P2) == tuple(P1 & P2)
        assert tuple(~DM) == tuple(~PM)
        assert (D1.width, D1.height, D1.is_empty) == (P1.width, P1.height, P1.is_empty)
        assert tuple(Rect(*r1).normalize()) == tuple(pymupdf.Rect(*r1).normalize())


def test_points_turn_exactly_as_pymupdfs_point_does():
    """The text layer turns every character origin on a rotated page through `transform_point`, and it must
    give PyMuPDF's two numbers. (PyMuPDF's Point will not take TrueDoc's Matrix: it reads it as the
    identity, which is how stage C first left every origin on a turned page where it was.)"""
    pymupdf = pytest.importorskip("pymupdf")
    rng = random.Random(11)
    for _ in range(3000):
        w, h = rng.uniform(100, 1400), rng.uniform(100, 1400)
        m = rng.choice([(0, 1, -1, 0, h, 0), (-1, 0, 0, -1, w, h), (0, -1, 1, 0, 0, w),
                        (0.8, 0.6, -0.6, 0.8, rng.uniform(-50, 50), rng.uniform(-50, 50))])
        pt = (rng.uniform(-50, 1500), rng.uniform(-50, 1500))
        want = pymupdf.Point(pt) * pymupdf.Matrix(*m)
        assert transform_point(pt, Matrix(*m)) == (want.x, want.y)
