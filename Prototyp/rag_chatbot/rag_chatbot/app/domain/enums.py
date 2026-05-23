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


class IngestStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
