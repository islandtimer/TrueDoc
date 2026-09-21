"""Put the pilot's questions on disk, page by page, so a helper can be asked them again without my reading them.

The D039 pilot wrote its questions inside a workflow; the held-out half's never came back to me, and must not. To ask
those same questions of another reader, they have to reach a helper without passing my eyes: this reads them from the
run's journal (the workflow's own record of what each helper returned) and writes one file a page, under a name that
says nothing and is shared with none of that page's other files. It prints counts, and for the tuned-on half nothing
but page ids; never a word of a held-out page.

The pilot's own rule is repeated here so the same pages are chosen: in the order of the draw, the first `--take`
pages of each half whose writer called the page usable and wrote at least three questions.

usage (repo root, the project's venv): meaning_export_questions.py <pilot folder> <journal.jsonl> [--take 15]
"""
import hashlib
import json
import os
import sys


def option(name, default):
    return type(default)(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def main():
    folder, journal = sys.argv[1], sys.argv[2]
    take = option("--take", 15)
    manifest = json.load(open(os.path.join(folder, "manifest_private.json"), encoding="utf-8"))
    order = [e["pid"] for e in manifest["pages"]]          # the order of the draw
    seed = manifest["seed"]

    written = {}
    for line in open(journal, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("type") != "result":
            continue
        blob = json.dumps(row, ensure_ascii=False)
        if '"questions"' not in blob or "/write" not in blob:
            continue
        # the writer's return, wherever the journal keeps it
        found = None
        stack = [row]
        while stack and found is None:
            here = stack.pop()
            if isinstance(here, dict):
                if isinstance(here.get("task_id"), str) and here["task_id"].endswith("/write") and "questions" in here:
                    found = here
                else:
                    stack.extend(here.values())
            elif isinstance(here, list):
                stack.extend(here)
            elif isinstance(here, str) and here.lstrip().startswith("{") and '"questions"' in here:
                try:
                    stack.append(json.loads(here))
                except ValueError:
                    pass
        if found is not None:
            pid = found["task_id"].split("/")[0]
            written.setdefault(pid, found)                  # the first run's, where a replay wrote a second

    out_dir = os.path.join(folder, "qold")
    os.makedirs(out_dir, exist_ok=True)
    chosen, counts = [], {"t": 0, "h": 0}
    for half in ("t", "h"):
        for pid in [p for p in order if p.startswith(half)]:
            if counts[half] >= take:
                break
            w = written.get(pid)
            if not w or not w.get("usable") or len(w.get("questions") or []) < 3:
                continue
            # ids carry an "o" (for the older set), so that a helper asked these and a newer set at once cannot confuse them
            qs = [{"id": "o%d" % (i + 1), "kind": q["kind"], "answer_type": q["answer_type"],
                   "question": q["question"], "answer": q["answer"]} for i, q in enumerate(w["questions"])]
            name = hashlib.sha1(("%s|%s|questions-of-the-pilot" % (seed, pid)).encode("utf-8")).hexdigest()[:14]
            path = os.path.join(out_dir, name + ".json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"questions": qs}, f, indent=1, ensure_ascii=False)
            chosen.append({"pid": pid, "held_out": pid.startswith("h"), "questions": len(qs),
                           "qold": os.path.abspath(path).replace("\\", "/")})
            counts[half] += 1
    with open(os.path.join(folder, "qold_index.json"), "w", encoding="utf-8") as f:
        json.dump(chosen, f, indent=1)
    print("writers found in the journal: %d | pages written: tuned-on %d, held out %d | questions: %d"
          % (len(written), counts["t"], counts["h"], sum(c["questions"] for c in chosen)))
    print("tuned-on pages:", " ".join(c["pid"] for c in chosen if not c["held_out"]))
    print("held-out pages: %d, not named" % counts["h"])


if __name__ == "__main__":
    main()
