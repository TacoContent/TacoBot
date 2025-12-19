import os
from pathlib import Path

# Base directory is the parent of the 'modules' directory (i.e., scripts/minecraft)
BASE_DIR = Path(__file__).parent.parent.resolve()

JARS_DIR = BASE_DIR / "jars"
OUTPUT_DIR = BASE_DIR / "output"
ASSETS_DIR = OUTPUT_DIR / "assets"
METADATA_FILE = OUTPUT_DIR / "items.json"

# Environment Variables
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")

# Ensure directories exist
JARS_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
