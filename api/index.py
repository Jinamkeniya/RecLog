import os
import sys

# Add project root to path so Flask app and its imports resolve correctly
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from app import app
