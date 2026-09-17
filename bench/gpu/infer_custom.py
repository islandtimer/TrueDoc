"""On the GPU machine: read a folder of one-page PDFs with Infinity-Parser2 under a prompt of ours.

    python3 infer_custom.py <pdf_dir> <out_dir> <prompt file>

The authors' infer.py asks for their layout task, which calls a picture a "figure" and transcribes
nothing in it. TrueDoc asks a picture on a digital page a different question - is there text in
you, and what does it say - so the crops are read again under that question, through the same
client and the same served model. Writes <out_dir>/inference.jsonl, one {"pdf", "markdown"} a line,
the form place_bakeoff.py reads.
"""
import json
import os
import sys
from pathlib import Path

from infinity_parser2 import InfinityParser2

pdf_dir, out_dir, prompt_file = sys.argv[1:4]
with open(prompt_file, encoding="utf-8") as f:
    prompt = f.read().strip()
kwargs = {"task_type": "custom", "custom_prompt": prompt, "output_format": "md", "pages": "1"}
parser = InfinityParser2(model_name="inf-mllm", backend="vllm-server",
                         api_url="http://localhost:8000/v1/chat/completions", api_key="EMPTY")
pdfs = sorted(str(p) for p in Path(pdf_dir).rglob("*.pdf"))
os.makedirs(out_dir, exist_ok=True)
done = failed = 0
with open(os.path.join(out_dir, "inference.jsonl"), "a", encoding="utf-8") as out:
    for start in range(0, len(pdfs), 16):
        batch = pdfs[start:start + 16]
        try:
            results = parser.parse(batch, batch_size=16, **kwargs)
            if isinstance(results, str):
                results = [results]
        except Exception:  # one bad page must not take its batch with it
            results = []
            for pdf in batch:
                try:
                    results.append(parser.parse(pdf, batch_size=1, **kwargs))
                except Exception as exc:
                    failed += 1
                    print("FAILED", pdf, repr(exc)[:200])
                    results.append("")
        for pdf, text in zip(batch, results):
            out.write(json.dumps({"pdf": pdf, "markdown": text or ""}, ensure_ascii=False) + "\n")
            out.flush()
            done += 1
print("[custom] done. parsed=%d failed=%d total=%d" % (done, failed, len(pdfs)))
