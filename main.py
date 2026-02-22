#!/usr/bin/env python3
"""
Main entry point for Robot Agent Module
"""

import sys
import os

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simulation_runner import main

if __name__ == "__main__":
    main()