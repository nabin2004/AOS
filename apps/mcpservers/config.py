import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent
DOCS_PATH = Path(os.getenv("MANIM_DOCS_PATH", BASE_DIR / "manim_kb.md"))
INDEX_PATH = Path(os.getenv("MANIM_INDEX_PATH", BASE_DIR / ".cache" / "manim_index.pkl"))

# Embedding model
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "google/embeddinggemma-300m")
EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "32"))

# Search defaults
SEARCH_TOP_K = int(os.getenv("SEARCH_TOP_K", "5"))
