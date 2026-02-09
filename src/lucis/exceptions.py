"""
Custom exceptions for Lucis.

Exceptions hierarchy:
    LucisError (base)
    ├── LucisEmptyCorpusError    - Empty corpus
    ├── LucisInvalidDocumentError - Invalid document
    ├── LucisEngineError         - Engine error
    └── LucisSearchError         - Search error
"""


class LucisError(Exception):
    """Base Exception for Lucis."""
    pass


class LucisEmptyCorpusError(LucisError):
    """Raised when the corpus is empty or has no valid documents."""
    
    def __init__(self, message: str = "The corpus is empty or contains no valid documents"):
        super().__init__(message)


class LucisInvalidDocumentError(LucisError):
    """Raised when a document is invalid (wrong type, etc.)."""
    
    def __init__(self, doc_index: int | None = None, detail: str = ""):
        if doc_index is not None:
            message = f"Invalid document at index {doc_index}"
        else:
            message = "Invalid document"
        
        if detail:
            message += f": {detail}"
        
        super().__init__(message)
        self.doc_index = doc_index


class LucisEngineError(LucisError):
    """Raised when there is an error related to the computation engine."""
    
    def __init__(self, engine_name: str, detail: str = ""):
        message = f"Error in engine '{engine_name}'"
        if detail:
            message += f": {detail}"
        super().__init__(message)
        self.engine_name = engine_name


class LucisSearchError(LucisError):
    """Raised when there is an error during search."""
    
    def __init__(self, query: str = "", detail: str = ""):
        message = "Error during search"
        if query:
            message += f" for query '{query[:50]}...'" if len(query) > 50 else f" for query '{query}'"
        if detail:
            message += f": {detail}"
        super().__init__(message)
        self.query = query


class LucisTokenizationError(LucisError):
    """Raised when there is an error during tokenization."""
    
    def __init__(self, detail: str = "Error during tokenization"):
        super().__init__(detail)
