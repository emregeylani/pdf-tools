"""Allows running the package directly: python3 -m pdf_tools"""
import sys
import os

# Ensure the project root is on the path when invoked as 'python3 pdf_tools'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdf_tools.cli import cli

if __name__ == "__main__":
    cli()
