#!/usr/bin/env python3
"""
clean_pdf.py - remove information from a long PDF with a LOCAL model (Ollama).

You decide WHAT to remove by writing it in prompt.txt.
The PDF is processed a few pages at a time, so even 100+ pages work.
If you stop it (Ctrl+C), just run it again - finished parts are skipped.

Usage (inside ~/local-llm-test with the venv active):
    python clean_pdf.py input/mydocument.pdf
Result:
    output/mydocument_cleaned.txt
"""
import re
import sys
import time
from pathlib import Path

import pymupdf as fitz 
import requests

# ---------------- settings ----------------
MODEL = "qwen3:8b"       # any model you pulled with: ollama pull <name>
PAGES_PER_CHUNK = 2      # pages sent to the model at once (2 is safe for 16 GB RAM)
# ------------------------------------------

BASE = Path(__file__).resolve().parent
OLLAMA = "http://127.0.0.1:11434/api/chat"

SYSTEM = (
    "You are a text-cleaning tool. You receive RULES and a TEXT. "
    "Return the COMPLETE text, unchanged, except that every piece of information "
    "described in the RULES is replaced with [REMOVED]. "
    "Do not summarize, shorten, translate, explain or add comments. "
    "Output only the cleaned text."
)


def ask_model(rules, text):
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"RULES:\n{rules}\n\nTEXT:\n{text}"},
        ],
        "stream": False,
        "think": False,  # skip slow "thinking" mode on Qwen3-type models
        "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 4096},
    }
    r = requests.post(OLLAMA, json=payload, timeout=3600)
    if r.status_code == 400 and "think" in r.text.lower():   # model without thinking support
        payload.pop("think")
        r = requests.post(OLLAMA, json=payload, timeout=3600)
    r.raise_for_status()
    answer = r.json()["message"]["content"]
    return re.sub(r"<think>.*?</think>", "", answer, flags=re.DOTALL).strip()


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    pdf_path = Path(sys.argv[1])
    rules = (BASE / "prompt.txt").read_text(encoding="utf-8").strip()
    if not rules:
        sys.exit("prompt.txt is empty - write your removal rules there first.")

    try:
        requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
    except requests.RequestException:
        sys.exit("Cannot reach Ollama. Is the SSH tunnel open? (ssh -N -L 11434:127.0.0.1:11434 imon333@192.168.0.106)")

    with fitz.open(pdf_path) as pdf:
        pages = [page.get_text() for page in pdf]
    if sum(len(p.strip()) for p in pages) < 100 * len(pages):
        print("! Very little text found - this PDF is probably scanned. Run ocrmypdf first (see guide).")

    parts_dir = BASE / "output" / f"{pdf_path.stem}_parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    chunks = [pages[i:i + PAGES_PER_CHUNK] for i in range(0, len(pages), PAGES_PER_CHUNK)]
    print(f"{len(pages)} pages -> {len(chunks)} parts, model: {MODEL}")

    start = time.time()
    for n, chunk in enumerate(chunks, 1):
        part_file = parts_dir / f"part_{n:04d}.txt"
        if part_file.exists():
            continue                                   # already done in an earlier run
        first = (n - 1) * PAGES_PER_CHUNK + 1
        last = first + len(chunk) - 1
        text = "\n".join(chunk)
        if not text.strip():
            cleaned = ""
        else:
            t0 = time.time()
            print(f"Part {n}/{len(chunks)} (pages {first}-{last}) ...", end="", flush=True)
            cleaned = ask_model(rules, text)
            print(f" done in {time.time() - t0:.0f}s")
        part_file.write_text(f"===== Pages {first}-{last} =====\n{cleaned}\n", encoding="utf-8")

    out_file = BASE / "output" / f"{pdf_path.stem}_cleaned.txt"
    out_file.write_text(
        "\n".join(p.read_text(encoding="utf-8") for p in sorted(parts_dir.glob("part_*.txt"))),
        encoding="utf-8",
    )
    print(f"\nFinished in {(time.time() - start) / 60:.1f} min -> {out_file}")


if __name__ == "__main__":
    main()
