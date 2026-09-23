"""What made a conversion: the code, the options in force, the readers and where they ran, and the time it took.

A conversion that says only `truedoc/0.0.1` cannot be told from one made a week later by different code, and a
before-and-after measure is exactly that comparison: which commit, with the layout model or without, which reader read
the scanned pages and where. So every conversion carries the record, in its status and in its front matter.

The commit is found where it can be. Installed from a git address (`pip install git+...@<commit>`), pip keeps the
commit in the installation's `direct_url.json`. Run from a checkout - an editable install, a worktree on the path - git
is asked about the folder the package was imported from, and whether the package's own files differ from that commit.
Neither: the record says so, rather than guessing. Nothing in the record names a secret: an address is written without
its user name or password, and a key is never read here.
"""
from __future__ import annotations

import dataclasses
import functools
import json
import os
import platform
import subprocess
from urllib.parse import urlsplit, urlunsplit

from truedoc import __version__

_HERE = os.path.dirname(os.path.abspath(__file__))


def _git(root: str, *args: str) -> str | None:
    try:
        r = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, timeout=10)
    except Exception:
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def _without_credentials(address: str) -> str:
    try:
        parts = urlsplit(address)
    except ValueError:
        return address
    if not parts.scheme or "@" not in parts.netloc:
        return address
    return urlunsplit((parts.scheme, parts.netloc.rsplit("@", 1)[1], parts.path, parts.query, parts.fragment))


@functools.lru_cache(maxsize=1)
def code() -> dict:
    """The package's version and, where it can be found, the commit it was built from."""
    out: dict = {"package": __version__, "python": platform.python_version()}
    try:
        from importlib.metadata import distribution

        raw = distribution("truedoc").read_text("direct_url.json")
        record = json.loads(raw) if raw else {}
    except Exception:
        record = {}
    commit = (record.get("vcs_info") or {}).get("commit_id")
    if commit:
        out["commit"] = commit
        out["installed_from"] = _without_credentials(record.get("url", ""))
        return out
    root = os.path.dirname(_HERE)
    if os.path.exists(os.path.join(root, ".git")):
        head = _git(root, "rev-parse", "HEAD")
        if head:
            out["commit"] = head
            changed = _git(root, "status", "--porcelain", "--", os.path.basename(_HERE))
            out["modified"] = bool(changed)
            return out
    out["commit"] = None
    return out


def _where(endpoint: str) -> str:
    spec = (endpoint or "").strip()
    if spec.lower().startswith("file:"):
        return "readings replayed from disk"
    if spec.lower().startswith("anthropic"):
        return "the Anthropic API"
    return _without_credentials(spec)


def _layout() -> dict:
    from truedoc.layout.docling_layout import get_detector

    detector = get_detector()
    out = {"model": detector.repo_id}
    model = getattr(detector, "_model", None)
    revision = getattr(getattr(model, "config", None), "_commit_hash", None) if model is not None else None
    if revision:
        out["revision"] = revision
    try:
        # The same weights run by another release of the libraries that run them can place a region differently.
        from importlib.metadata import version

        out["runtime"] = {"transformers": version("transformers"), "torch": version("torch")}
    except Exception:
        pass
    return out


def _ocr() -> dict:
    out: dict = {"engine": "rapidocr_onnxruntime"}
    try:
        from importlib.metadata import version

        out["version"] = version("rapidocr_onnxruntime")
    except Exception:
        pass
    try:
        # Looked for on disk only: asking the OCR module for it would fetch it, and a record must not download.
        from truedoc.ocr.rapid import _EN_REC_FILE, _MODELS_DIR

        local = os.path.join(_MODELS_DIR, _EN_REC_FILE.replace("/", os.sep))
        english = os.environ.get("TRUEDOC_OCR_LANG", "en").lower() == "en" and os.path.exists(local)
        out["recognition"] = os.path.basename(local) if english else "the engine's own"
    except Exception:
        pass
    return out


def _options(opts) -> dict:
    out = dataclasses.asdict(opts)
    for key in ("vision_endpoint", "vision_deep"):
        if out.get(key):
            out[key] = _without_credentials(out[key])
    return out


def record(opts, seconds: float, doc=None) -> dict:
    """The build record of one conversion: code, options, readers, and the seconds it took to read the document."""
    readers: dict = {}
    try:
        import pypdfium2.version as pdfium_version

        readers["pdf"] = {"pypdfium2": str(pdfium_version.PYPDFIUM_INFO), "pdfium": str(pdfium_version.PDFIUM_INFO)}
    except Exception:
        pass
    ran_layout = opts.layout and not any((p.meta.get("layout_unavailable") for p in (doc.pages if doc else [])))
    if opts.layout:
        try:
            readers["layout"] = dict(_layout(), ran=bool(ran_layout))
        except Exception as exc:
            readers["layout"] = {"ran": False, "why": repr(exc)[:120]}
    if opts.ocr:
        readers["ocr"] = dict(_ocr(), ran=bool(doc is not None and doc.metadata.get("pages_with_ocr")))
    if opts.vision_endpoint:
        readers["vision"] = {"model": opts.vision_model, "where": _where(opts.vision_endpoint)}
    if opts.vision_deep:
        readers["deep"] = {"model": opts.vision_deep_model or None, "where": _where(opts.vision_deep)}
    return {"code": code(), "options": _options(opts), "readers": readers, "seconds": round(seconds, 2)}
