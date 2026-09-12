"""On the GPU machine: read benchmark pages with TeleOCR and write one markdown file per page.

    python3 teleocr_pages.py <pdf folder> <output folder> [pages per batch]

TeleOCR is not a whole-page reader. Its own recipe is a pipeline: analyse the layout, crop each
block, then ask a different question of each kind of block - text, table (answered in OTSL, which
its helper turns into HTML), formula (answered in LaTeX). That pipeline is most of why it tops
OmniDocBench, and it is also, awkwardly, the same shape as TrueDoc's own.

So this asks it two ways on every page, and writes both, because the comparison we need is not
"which is better" in the abstract but "can this model read our hard pages at all":

  whole/<stem>.md   one call for the whole page, the same question olmOCR and the frontier reader
                    are asked. Directly comparable to the numbers we already have (olmOCR 239 of
                    517 checks, Claude with a good prompt 273).
  layout/<stem>.md  its own pipeline: layout, then a question per block, assembled in reading
                    order. Slower, and the way it is meant to be used.

Expects: a CUDA machine, python3 with torch and transformers, internet for Hugging Face.
"""
import json
import os
import sys
import time
import traceback

import torch
from PIL import Image
from transformers import AutoModel, AutoProcessor

MODEL_ID = os.environ.get("TELEOCR_MODEL", "StarDoc-AI/TeleOCR")
LONGEST = int(os.environ.get("TELEOCR_LONGEST", "1568"))
LAYOUT_SIZE = 1036

WHOLE_PAGE_PROMPT = (
    "Please output the text content from the image. Convert equations to LaTeX and tables to "
    "markdown, and give the text in the order a person would read it."
)
BLOCK_PROMPTS = {
    "text": "Please output the text content from the image.",
    "title": "Please output the text content from the image.",
    "table": "This is the image of a table. Please output the table in OTSL format.",
    "equation": "Please write out the expression of the formula in the image using LaTeX format.",
    "code": "The image contains a code snippet, please output the parsing result.",
}


def render(pdf_path: str, longest: int = LONGEST) -> Image.Image:
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(pdf_path)
    try:
        page = doc[0]
        scale = longest / max(page.get_width(), page.get_height())
        return page.render(scale=scale).to_pil().convert("RGB")
    finally:
        doc.close()


def main() -> None:
    pdf_root, out_root = sys.argv[1], sys.argv[2]
    processor = AutoProcessor.from_pretrained(MODEL_ID, trust_remote_code=True, use_fast=True)
    model = AutoModel.from_pretrained(MODEL_ID, trust_remote_code=True, torch_dtype=torch.bfloat16).cuda().eval()

    def infer(image: Image.Image, prompt: str, max_new_tokens: int = 4096) -> str:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]},
        ]
        chat = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = processor(text=[chat], images=[image], padding=True, return_tensors="pt").to(
            device=model.device, dtype=model.dtype)
        out = model.generate(**inputs, use_cache=True, max_new_tokens=max_new_tokens, do_sample=False)
        out = out.cpu().tolist()[0][len(inputs.input_ids[0]):]
        return processor.batch_decode([out], skip_special_tokens=True,
                                      clean_up_tokenization_spaces=False)[0].strip()

    pdfs = []
    for root, _dirs, files in os.walk(pdf_root):
        for name in sorted(files):
            if name.lower().endswith(".pdf"):
                pdfs.append(os.path.join(root, name))
    print(f"{len(pdfs)} pages to read", flush=True)

    for mode in ("whole", "layout"):
        os.makedirs(os.path.join(out_root, mode), exist_ok=True)

    for i, pdf in enumerate(pdfs, 1):
        stem = os.path.splitext(os.path.basename(pdf))[0]
        started = time.time()
        try:
            page = render(pdf)
        except Exception as exc:
            print(f"{i:4d}/{len(pdfs)} {stem}: could not render: {exc}", flush=True)
            continue

        whole_path = os.path.join(out_root, "whole", stem + ".md")
        if not os.path.exists(whole_path):
            try:
                text = infer(page, WHOLE_PAGE_PROMPT)
            except Exception:
                text = ""
                traceback.print_exc()
            with open(whole_path, "w", encoding="utf-8") as fh:
                fh.write(text)

        layout_path = os.path.join(out_root, "layout", stem + ".md")
        if not os.path.exists(layout_path):
            try:
                small = page.resize((LAYOUT_SIZE, LAYOUT_SIZE), Image.Resampling.BICUBIC)
                raw = infer(small, "Analyze the image layout.", max_new_tokens=2048)
                blocks = json.loads(raw) if raw.strip().startswith(("[", "{")) else []
                if isinstance(blocks, dict):
                    blocks = blocks.get("blocks") or blocks.get("layout") or []
                parts = []
                for b in blocks:
                    kind = str(b.get("type") or b.get("category") or "text").lower()
                    box = b.get("bbox") or b.get("box")
                    if not box or len(box) != 4:
                        continue
                    x0, y0, x1, y1 = [float(v) for v in box]
                    if max(x1, y1) <= 1.5:            # normalised
                        x0, y0, x1, y1 = x0 * page.width, y0 * page.height, x1 * page.width, y1 * page.height
                    else:                              # in the 1036-square the layout saw
                        sx, sy = page.width / LAYOUT_SIZE, page.height / LAYOUT_SIZE
                        x0, y0, x1, y1 = x0 * sx, y0 * sy, x1 * sx, y1 * sy
                    crop = page.crop((max(0, int(x0)), max(0, int(y0)),
                                      min(page.width, int(x1)), min(page.height, int(y1))))
                    if crop.width < 8 or crop.height < 8:
                        continue
                    prompt = BLOCK_PROMPTS.get(kind, BLOCK_PROMPTS["text"])
                    answer = infer(crop, prompt, max_new_tokens=2048)
                    if kind == "table":
                        answer = "<table-otsl>" + answer + "</table-otsl>"
                    elif kind == "equation":
                        answer = "$$" + answer.strip().removeprefix("$$").removesuffix("$$").strip() + "$$"
                    if answer.strip():
                        parts.append(answer.strip())
                page_text = "\n\n".join(parts)
            except Exception:
                page_text = ""
                traceback.print_exc()
            with open(layout_path, "w", encoding="utf-8") as fh:
                fh.write(page_text)

        print(f"{i:4d}/{len(pdfs)} {stem}: {time.time() - started:.1f}s", flush=True)

    print("done", flush=True)


if __name__ == "__main__":
    main()
