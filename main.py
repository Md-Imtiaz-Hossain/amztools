"""
Amazon Wholesale Catalog Suite - CLI & Programmatic Entrypoint
==============================================================
Purpose:
    Command-line and programmatic entrypoint for the multi-module project.
    Allows running the Streamlit dashboard or invoking individual modules
    programmatically.

Usage:
    # Run full Streamlit web application:
    python main.py

    # Inspect module architecture:
    python main.py --help
"""

import argparse
import sys
import subprocess
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def main():
    parser = argparse.ArgumentParser(
        description="Amazon Wholesale Catalog Suite & Cloudflare D1 Pipeline"
    )
    parser.add_argument(
        "--run-ui",
        action="store_true",
        default=True,
        help="Launch the Streamlit web interface (default)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8501,
        help="Port to run Streamlit on (default: 8501)",
    )
    args = parser.parse_args()

    app_path = os.path.join(PROJECT_ROOT, "streamlit_app.py")
    cmd = [sys.executable, "-m", "streamlit", "run", app_path, "--server.port", str(args.port)]
    print(f"🚀 Launching Amazon Wholesale Multi-Module Application: {' '.join(cmd)}")
    subprocess.run(cmd)


if __name__ == "__main__":
    main()
