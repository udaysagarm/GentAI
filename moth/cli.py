import argparse
import subprocess
import sys
import os

def main():
    parser = argparse.ArgumentParser(description="Moth Ecosystem CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: moth start
    start_parser = subparsers.add_parser("start", help="Launch the Web UI")

    # Command: moth install <feature>
    install_parser = subparsers.add_parser("install", help="Install a plugin")
    install_parser.add_argument("feature", help="Name of feature (e.g. spotify)")

    args = parser.parse_args()

    if args.command == "start":
        print("🦋 Moth AI is waking up...")
        # Get path to the internal app.py
        package_dir = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(package_dir, "app.py")
        # Use sys.executable to ensure we run streamlit from the *current* virtual environment
        # and not the global one found in PATH (which was checking /opt/anaconda3)
        subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])
        
    elif args.command == "install":
        print(f"📦 Installing feature: {args.feature}...")
        print("(Plugin system coming in Phase 2)")
        
    else:
        parser.print_help()
