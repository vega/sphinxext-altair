import os
import sys

source_dir = os.path.abspath(".")
if source_dir not in sys.path:
    sys.path.insert(0, source_dir)

project = "test-altairplot"
extensions = ["sphinxext_altair.altairplot"]
exclude_patterns = ["_build"]
