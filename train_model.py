#!/usr/bin/env python3
"""
Script to train the content-based recommendation model.
This script runs the full training pipeline and saves artifacts.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.training.train import main

if __name__ == "__main__":
    main()
