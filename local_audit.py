# local_audit.py
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def scan_for_pattern(patterns, path):
    hits = []
    for p in path.rglob("*.py"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pat in patterns:
            if pat in text:
                hits.append((p.name, pat))
    return hits

def main():
    print("=== AWARDS local audit ===")
    print("Root:", ROOT)

    py_files = list(ROOT.rglob("*.py"))
    print("Python files:", len(py_files))

    risky = [
        ("PRAGMA key = '", "Raw SQLCipher key interpolation"),
        ("f\"PRAGMA key", "Dynamic PRAGMA key"),
        ("eval(", "eval usage"),
        ("exec(", "exec usage"),
        ("os.system(", "os.system usage"),
        ("subprocess.call(", "subprocess call"),
        ("sqlite3.connect(", "sqlite connect"),
    ]
    for name, desc in risky:
        found = []
        for p in py_files:
            try:
                t = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if name in t:
                found.append(str(p.relative_to(ROOT)))
        if found:
            print(f"\n[{desc}]")
            for f in found:
                print(" -", f)

    # Look for demo DB/password mention
    demo_db = ROOT / "awards_0v4e.db"
    if demo_db.exists():
        print("\n[demo DB]")
        print(" - demo DB exists:", demo_db)

    readme = ROOT / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8", errors="ignore")
        if "пароль демонстраційної бази" in text.lower() or "demo password" in text.lower() or "Пароль демонстраційної бази" in text:
            print(" - README contains demo DB password instructions")

    # basic complexity scan
    print("\n[large files]")
    for p in sorted(py_files, key=lambda x: x.stat().st_size, reverse=True)[:10]:
        print(f" - {p.name}: {p.stat().st_size} bytes")

    print("\n[done]")

if __name__ == "__main__":
    main()
