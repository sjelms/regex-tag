"""Test package bootstrap for local src imports."""

import os
import sys


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
