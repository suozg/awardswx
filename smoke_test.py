# smoke_test.py
import importlib
import sys

MODULES = [
    "config",
    "database_logic",
    "ui_utils",
    "main",
    "settings_manager",
    "search_tab",
    "kartka",
    "zvity",
    "setuptab",
    "dovidnyk",
    "tablaw",
    "websearch",
    "sql_console",
    "graph",
    "info",
    "gameoflife"
]

def main():
    print("=== smoke import test ===")
    for name in MODULES:
        try:
            importlib.import_module(name)
            print(f"[OK] {name}")
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
    print("done")

if __name__ == "__main__":
    main()
