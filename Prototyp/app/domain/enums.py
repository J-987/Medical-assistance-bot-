from enum import Enum


class LoaderType(str, Enum):
    UNSTRUCTURED = "unstructured"
    MARKER = "marker"
    PYMUPDF = "pymupdf"
    AUTO = "auto"


class ChunkStrategy(str, Enum):
    SEMANTIC = "semantic"
    RECURSIVE = "recursive"
    FIXED = "fixed"


class FileType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    HTML = "html"
    MARKDOWN = "md"
    IMAGE = "image"
    UNKNOWN = "unknown"


class EmbeddingModel(str, Enum):
    NOMIC = "nomic-embed-text"
    MXBAI = "mxbai-embed-large"
    ALL_MINILM = "all-minilm"


class ChatModel(str, Enum):
    LLAMA3 = "llama3.2"
    MISTRAL = "mistral"
    PHI3 = "phi3"
    GEMMA2 = "gemma2"
    QWEN25 = "qwen2.5"
    # Kleinere Modelle für Rechner mit wenig Speicher/RAM
    LLAMA3_1B = "llama3.2:1b"      # ~1,3 GB
    QWEN25_15B = "qwen2.5:1.5b"    # ~1,0 GB
    QWEN25_05B = "qwen2.5:0.5b"    # ~0,4 GB


class IngestStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExplainMode(str, Enum):
    """Scaffolding-Stufe der Erklärung (Wood, Bruner & Ross, 1976).

    Regelt das Hilfe-Level analog zur Zone of Proximal Development:
    von maximaler Unterstützung (EINFACH) bis geringer Unterstützung
    mit Originalbegriffen (DETAILLIERT).
    """
    EINFACH = "einfach"        # Sprachniveau ~A2, kurze Sätze, viele Analogien
    STANDARD = "standard"      # ~B1, Fachbegriffe werden erklärt (Default)
    DETAILLIERT = "detailliert"  # Originalbegriffe + Erklärung, mehr Tiefe
