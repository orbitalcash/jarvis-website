"""
Lanceur du site web public JARVIS AI
Usage : python run.py
URL   : http://localhost:8080
"""
import sys
import subprocess
from pathlib import Path

HERE = Path(__file__).parent

def check_deps():
    missing = []
    for pkg in ("fastapi", "uvicorn", "jinja2"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Installation des dépendances manquantes : {missing}")
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing, stdout=subprocess.DEVNULL)
        print("Dépendances installées.")

if __name__ == "__main__":
    check_deps()
    import os, uvicorn
    os.chdir(str(HERE))
    sys.path.insert(0, str(HERE))
    print("\n" + "="*55)
    print("  JARVIS AI — Site Web Public")
    print("  http://localhost:8080")
    print("  Ctrl+C pour arreter")
    print("="*55 + "\n")
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        log_level="info",
    )
