"""
CLI Entry Point

Launch the Streamlit web application.
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Launch EcoParse Streamlit application."""
    main_py_path = Path(__file__).parent / "main.py"
    command = [sys.executable, "-m", "streamlit", "run", str(main_py_path)]

    try:
        subprocess.run(command, check=True)
    except FileNotFoundError:
        print("Error: 'streamlit' not found. Is Streamlit installed?")
    except subprocess.CalledProcessError as e:
        print(f"Error running app: {e}")

if __name__ == "__main__":
    main()