"""
fix_encoding.py

Fixes UTF-8-read-as-Latin-1 mojibake (e.g. "VITÂ·01" -> "VIT·01",
"one-time load â€” no auto-polling" -> "one-time load — no auto-polling")
across all source files under src/.

Run from the `frontend` directory:
    python fix_encoding.py

It's safe to run more than once (a clean file just won't change).
"""

from pathlib import Path

ROOT = Path("src")
EXTENSIONS = {".ts", ".tsx", ".css", ".json", ".html"}

# Ordered longest-pattern-first so overlapping sequences (e.g. the "â€"
# prefix shared by em-dash and curly-quote mojibake) resolve correctly.
REPLACEMENTS = [
    ("â€”", "—"),   # em dash
    ("â€“", "–"),   # en dash
    ("â€¦", "…"),   # ellipsis
    ("â€™", "'"),   # right single quote / apostrophe
    ("â€˜", "'"),   # left single quote
    ("â€œ", "\u201c"),  # left double quote
    ("â€\x9d", "\u201d"),  # right double quote (raw byte form)
    ("â€", "\u201d"),  # right double quote (fallback, must come after em/en dash)
    ("Â·", "·"),    # middle dot
    ("Â®", "®"),    # registered trademark
    ("Â©", "©"),    # copyright
    ("Â ", "\u00a0"),  # non-breaking space
    ("Ã©", "é"),
    ("Ã¨", "è"),
    ("Ã¼", "ü"),
    ("Ã¶", "ö"),
    ("Ã±", "ñ"),
]


def fix_text(text: str) -> str:
    for bad, good in REPLACEMENTS:
        text = text.replace(bad, good)
    return text


def main():
    changed = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in EXTENSIONS:
            continue
        original = path.read_text(encoding="utf-8", errors="replace")
        fixed = fix_text(original)
        if fixed != original:
            path.write_text(fixed, encoding="utf-8", newline="")
            changed.append(str(path))

    if changed:
        print(f"Fixed {len(changed)} file(s):")
        for f in changed:
            print(" -", f)
    else:
        print("No mojibake found — nothing changed.")


if __name__ == "__main__":
    main()