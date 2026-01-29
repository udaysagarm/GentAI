import argparse
import subprocess
import sys
import os

def main():
    parser = argparse.ArgumentParser(description="GentAI Ecosystem CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: gent start
    start_parser = subparsers.add_parser("start", help="Launch the Web UI")

    # Command: gent install <feature>
    install_parser = subparsers.add_parser("install", help="Install a plugin")
    install_parser.add_argument("feature", help="Name of feature (e.g. spotify)")

    args = parser.parse_args()

    if args.command == "start":
        print("🚀 Starting GentAI Dashboard...")
        # Get path to the internal app.py
        package_dir = os.path.dirname(os.path.abspath(__file__))
        app_path = os.path.join(package_dir, "app.py")
        subprocess.run(["streamlit", "run", app_path])
        
    elif args.command == "install":
        print(f"📦 Installing feature: {args.feature}...")
        print("(Plugin system coming in Phase 2)")
        
    else:
        parser.print_help()
