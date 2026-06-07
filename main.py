"""
main.py
-------
Entry point for the GitHub Repository Analyzer.

Run:
    python main.py

Optional: pass a GitHub personal access token as the first CLI argument
to raise your API rate limit from 60 to 5 000 requests per hour:
    python main.py ghp_xxxxxxxxxxxxxxxxxxxx
"""

import sys
import tkinter as tk
from tkinter import messagebox


def check_dependencies():
    """Verify all required packages are installed before launching the GUI."""
    required = {
        'github':    'PyGithub',
        'pandas':    'pandas',
        'numpy':     'numpy',
        'matplotlib':'matplotlib',
        'seaborn':   'seaborn',
        'plotly':    'plotly',
        'networkx':  'networkx',
        'reportlab': 'reportlab',
        'openpyxl':  'openpyxl',
    }
    missing = []
    for module, package in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)

    if missing:
        msg = (
            "The following required packages are not installed:\n\n"
            + '\n'.join(f'  • {p}' for p in missing)
            + "\n\nInstall them with:\n"
            "  pip install -r requirements.txt"
        )
        # Try to show a GUI error dialog, fall back to console
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror('Missing Dependencies', msg)
            root.destroy()
        except Exception:
            print(msg, file=sys.stderr)
        sys.exit(1)


def main():
    check_dependencies()

    from gui import GitHubAnalyzerApp

    root = tk.Tk()

    # DPI awareness on Windows
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    # Pre-fill token if supplied as CLI argument
    app = GitHubAnalyzerApp(root)
    if len(sys.argv) > 1:
        app._token_var.set(sys.argv[1])

    root.mainloop()


if __name__ == '__main__':
    main()
