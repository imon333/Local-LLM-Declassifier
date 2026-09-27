# Local PDF Redactor

Remove confidential information from long PDF documents using a **local LLM**. The document never leaves your computer.

## Core idea

Cloud AI models are powerful, but you should not paste confidential documents into them.
This project adds a local "cleaning step" in front of the cloud:

```
Confidential PDF  →  local LLM removes sensitive data  →  cleaned text  →  safe to use with a cloud model
   (your PC)              (Ollama, offline)                 (your PC)
```

1. You describe **what** counts as confidential in plain language (`prompt.txt`).
2. The script extracts the text from the PDF and sends it, 2 pages at a time, to a model running locally in [Ollama](https://ollama.com).
3. The model returns the same text with every confidential item replaced by `[REMOVED]`.
4. All parts are joined into one cleaned text file.

Everything runs on `127.0.0.1` (localhost). No internet connection is needed after setup.

## Why process in parts?

A local model can only hold a limited amount of text at once (its *context window*).
Splitting the PDF into small parts means documents of 100+ pages work on a normal PC with 16 GB RAM.
Each part is saved immediately, so a stopped run can be resumed.

## Requirements

- Ubuntu (tested on 24.04), 16 GB RAM, no GPU needed
- [Ollama](https://ollama.com) with a model, e.g. `qwen3:8b`
- Python 3 with `venv`

## Setup

```bash
# 1. Ollama and a model
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3:8b

# 2. Project
git clone https://github.com/imon333/local-pdf-redactor.git
cd local-pdf-redactor
mkdir -p input output
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

1. Write your rules in `prompt.txt` (what to remove, what to keep).
2. Put your PDF into `input/`.
3. Run:

```bash
source venv/bin/activate
python clean_pdf.py input/mydocument.pdf
```

The result is written to `output/mydocument_cleaned.txt`.

Settings at the top of `clean_pdf.py`:

| Setting | Default | Meaning |
|---|---|---|
| `MODEL` | `qwen3:8b` | Any model installed in Ollama (`ollama list`) |
| `PAGES_PER_CHUNK` | `2` | Pages sent to the model per request |

## Testing

`examples/test_confidential.pdf` is an 8-page document with **fictional** personal data
(names, addresses, IBAN, passwords, IDs…). `examples/answer_key.txt` lists every item that should be removed.

```bash
cp examples/test_confidential.pdf input/
python clean_pdf.py input/test_confidential.pdf
```

Then search the output for the items in the answer key.

## Performance

CPU-only test machine: AMD Ryzen 5 3400G, 16 GB DDR4.
With `qwen3:8b`, one 2-page part takes several minutes, so large documents are best run overnight.
Smaller models (e.g. `qwen3:4b`) are about twice as fast but less accurate.

