#!/usr/bin/env python3
"""
Entry point for PX4 Setup Hub.
"""
import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from px4_hub.app import run_app

if __name__ == "__main__":
    run_app()
