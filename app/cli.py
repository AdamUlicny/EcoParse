"""
Command Line Interface Entry Point

Simple CLI wrapper for launching the Streamlit web application.
Provides a convenient way to start EcoParse from the command line.
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Launch the EcoParse Streamlit application."""
    main_py_path = Path(__file__).parent / "main.py"

    command = [
        sys.executable,  
        "-m",
        "streamlit",
        "run",
        str(main_py_path)
    ]

    try:
        subprocess.run(command, check=True)
    except FileNotFoundError:
        print("Error: 'streamlit' command not found. Is Streamlit installed correctly?")
    except subprocess.CalledProcessError as e:
        print(f"Error running the Streamlit app: {e}")

if __name__ == "__main__":
    main()