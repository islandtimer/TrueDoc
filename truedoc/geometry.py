"""Rectangles and affine matrices for page geometry, with PyMuPDF's exact semantics for the operations
TrueDoc uses, so that no stage needs PyMuPDF's types (M18, D007).

PyMuPDF keeps a rectangle's corners as Python floats but does its arithmetic in MuPDF's C code on 32-bit
floats: each operand is rounded to float32 on the way in and each result on the way out. So do these:
a single float32 multiplication, addition or division is reproduced exactly by doing it in double and
rounding the result, because a double carries more than twice a float's precision. Proved identical to
PyMuPDF on random input (D022) before any stage uses it.

A matrix (a, b, c, d, e, f) maps a point (x, y) to (a*x + c*y + e, b*x + d*y + f), PDF's convention.
"""
from __future__ import annotations

import struct
import sys

_FLT_EPSILON = 1.1920928955078125e-07
_PACK = struct.Struct("f")


def _f(x: float) -> float:
    """x rounded to the nearest 32-bit float."""
    return _PACK.unpack(_PACK.pack(x))[0]


class Matrix:
    """An affine matrix: Matrix(a, b, c, d, e, f), Matrix(sx, sy) for a scale, or Matrix(sequence of six)."""

    __slots__ = ("a", "b", "c", "d", "e", "f")

    def __init__(self, *args) -> None:
        if len(args) == 1:
            args = tuple(args[0])
        if len(args) == 2:
            args = (args[0], 0.0, 0.0, args[1], 0.0, 0.0)
        if len(args) != 6:
            raise ValueError("Matrix wants six numbers, two for a scale, or one sequence of six")
        self.a, self.b, self.c, self.d, self.e, self.f = (float(v) for v in args)

    def __iter__(self):
        return iter((self.a, self.b, self.c, self.d, self.e, self.f))

    def __len__(self) -> int:
        return 6

    def __getitem__(self, i):
        return (self.a, self.b, self.c, self.d, self.e, self.f)[i]

    def __invert__(self) -> "Matrix":
        """The inverse, as PyMuPDF computes it; all zeros where there is none."""
        a, b, c, d, e, f = (_f(v) for v in self)
        det = a * d - b * c
        if -sys.float_info.epsilon <= det <= sys.float_info.epsilon:
            return Matrix(0, 0, 0, 0, 0, 0)
        rdet = 1 / det
        na, nb, nc, nd = _f(d * rdet), _f(-b * rdet), _f(-c * rdet), _f(a * rdet)
        ne = _f(-e * na - f * nc)
        nf = _f(-e * nb - f * nd)
        return Matrix(na, nb, nc, nd, ne, nf)

    def __repr__(self) -> str:
        return f"Matrix{tuple(self)}"


def _point(x: float, y: float, m: tuple) -> tuple[float, float]:
    """MuPDF's fz_transform_point on float32s: x*a + y*c + e, each step rounded."""
    a, b, c, d, e, f = m
    return (_f(_f(_f(x * a) + _f(y * c)) + e), _f(_f(_f(x * b) + _f(y * d)) + f))


def transform_point(pt, m) -> tuple[float, float]:
    """A point through a matrix exactly as PyMuPDF's `Point(pt) * m` computes it: MuPDF's
    fz_transform_point, with the point and the matrix rounded to 32-bit floats on the way in.
    PyMuPDF's own Point cannot be given TrueDoc's Matrix: it reads a matrix it does not
    recognise as the identity, and every point stays where it was."""
    return _point(_f(pt[0]), _f(pt[1]), tuple(_f(v) for v in m))


class Rect:
    """A rectangle: Rect(x0, y0, x1, y1), Rect(sequence of four), or Rect(another rect)."""

    __slots__ = ("x0", "y0", "x1", "y1")

    def __init__(self, *args) -> None:
        if len(args) == 1:
            args = tuple(args[0])
        if len(args) != 4:
            raise ValueError("Rect wants four numbers or one sequence of four")
        self.x0, self.y0, self.x1, self.y1 = (float(v) for v in args)

    def __iter__(self):
        return iter((self.x0, self.y0, self.x1, self.y1))

    def __len__(self) -> int:
        return 4

    def __getitem__(self, i):
        return (self.x0, self.y0, self.x1, self.y1)[i]

    def __eq__(self, other) -> bool:
        try:
            return len(other) == 4 and tuple(self) == tuple(float(v) for v in other)
        except TypeError:
            return NotImplemented

    __hash__ = None

    @property
    def width(self) -> float:
        return max(0, self.x1 - self.x0)

    @property
    def height(self) -> float:
        return max(0, self.y1 - self.y0)

    @property
    def is_empty(self) -> bool:
        return self.x0 >= self.x1 or self.y0 >= self.y1

    def normalize(self) -> "Rect":
        if self.x1 < self.x0:
            self.x0, self.x1 = self.x1, self.x0
        if self.y1 < self.y0:
            self.y0, self.y1 = self.y1, self.y0
        return self

    def transform(self, m) -> "Rect":
        """MuPDF's fz_transform_rect, in place."""
        mm = tuple(_f(v) for v in (m if isinstance(m, Matrix) else Matrix(m)))
        a, b, c, d, _e, _f_ = mm
        x0, y0, x1, y1 = (_f(v) for v in self)
        if abs(b) < _FLT_EPSILON and abs(c) < _FLT_EPSILON:
            if a < 0:
                x0, x1 = x1, x0
            if d < 0:
                y0, y1 = y1, y0
            s, t = _point(x0, y0, mm), _point(x1, y1, mm)
            self.x0, self.y0, self.x1, self.y1 = s[0], s[1], t[0], t[1]
            return self
        if abs(a) < _FLT_EPSILON and abs(d) < _FLT_EPSILON:
            if b < 0:
                x0, x1 = x1, x0
            if c < 0:
                y0, y1 = y1, y0
            s, t = _point(x0, y0, mm), _point(x1, y1, mm)
            self.x0, self.y0, self.x1, self.y1 = s[0], s[1], t[0], t[1]
            return self
        invalid = x0 > x1 or y0 > y1
        pts = [_point(x0, y0, mm), _point(x0, y1, mm), _point(x1, y1, mm), _point(x1, y0, mm)]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        nx0, ny0, nx1, ny1 = min(xs), min(ys), max(xs), max(ys)
        if invalid:
            nx0, nx1, ny0, ny1 = nx1, nx0, ny1, ny0
        self.x0, self.y0, self.x1, self.y1 = nx0, ny0, nx1, ny1
        return self

    def __mul__(self, m) -> "Rect":
        if hasattr(m, "__float__"):
            return Rect(self.x0 * m, self.y0 * m, self.x1 * m, self.y1 * m)
        return Rect(self).transform(m)

    def include_rect(self, r) -> "Rect":
        """PyMuPDF's include_rect: an empty side leaves the other; otherwise the union, in float32."""
        r = Rect(r)
        if r.is_empty:
            return self
        if self.is_empty:
            self.x0, self.y0, self.x1, self.y1 = r.x0, r.y0, r.x1, r.y1
            return self
        self.x0, self.y0 = min(_f(self.x0), _f(r.x0)), min(_f(self.y0), _f(r.y0))
        self.x1, self.y1 = max(_f(self.x1), _f(r.x1)), max(_f(self.y1), _f(r.y1))
        return self

    def intersect(self, r) -> "Rect":
        """PyMuPDF's intersect: an empty operand is the answer (the other's own if it is empty);
        otherwise the overlap, in float32, which may come out inverted when there is none."""
        r = Rect(r)
        if r.is_empty:
            self.x0, self.y0, self.x1, self.y1 = r.x0, r.y0, r.x1, r.y1
            return self
        if self.is_empty:
            return self
        self.x0, self.y0 = max(_f(self.x0), _f(r.x0)), max(_f(self.y0), _f(r.y0))
        self.x1, self.y1 = min(_f(self.x1), _f(r.x1)), min(_f(self.y1), _f(r.y1))
        return self

    # No __ior__, as in PyMuPDF: `r |= s` makes a new rectangle rather than changing a shared one.
    def __or__(self, other) -> "Rect":
        return Rect(self).include_rect(other)

    def __and__(self, other) -> "Rect":
        return Rect(self).intersect(other)

    def __repr__(self) -> str:
        return f"Rect{tuple(self)}"
