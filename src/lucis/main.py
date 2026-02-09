import time
from typing import Any, Dict, List, Optional, Union
from .engines.core import CoreEngine
from .engines.base import DocId
from .storage.json_storage import JSONStorage
from .exceptions import LucisEngineError
from .models.search import SearchResult, SearchResponse

# Engine registry - maps friendly names to engine classes
# As new engines are added, register them here
_ENGINE_REGISTRY = {
    "core": CoreEngine,
    # Future: "plus": PlusEngine, "numpy": NumpyEngine, etc.
}


class Lucis:
    """
    The friendly face of Lucis.
    
    Lucis is an orchestrator (Facade pattern) that simplifies building
    custom search engines. It connects engines, storage, and tokenizers
    behind a clean, minimal API.

    Three ways to create a Lucis instance:
    1. From scratch with data:
        cp = Lucis.from_dict({"doc1": "hello world"}, name="my_search")
        cp = Lucis.from_list(["hello world"], name="my_search")
    
    2. Load an existing index from disk:
        cp = Lucis(name="my_search")  # Auto-loads if exists
    
    3. Empty instance for later use:
        cp = Lucis(name="my_search", autoload=False)
        cp.index(data)
    """

    def __init__(
        self, 
        name: str = "default",
        storage_dir: str = "lucis_data",
        engine: str = "core",
        autoload: bool = True,
    ):
        """
        Base constructor: sets up identity, storage, and engine.
        Does NOT ingest data — use .index(), .from_dict(), or .from_list() for that.

        Args:
            name: Identifier for the index. Used for persistence (filename/table).
            storage_dir: Directory where the JSON index files are stored.
            engine: Which engine to use. Currently supported: "core".
            autoload: If True and an index with this name exists on disk, load it automatically.
        """
        self.name = name
        self._is_indexed = False

        # 1. Configure storage
        # In v0.1.0 we only support JSONStorage
        # Future: detect storage type from config (SQL, Redis, etc.)
        self.storage = JSONStorage(directory=storage_dir)

        # 2. Configure engine
        # The registry pattern lets us add engines without touching Lucis's code
        engine_class = _ENGINE_REGISTRY.get(engine)
        if engine_class is None:
            available = ", ".join(_ENGINE_REGISTRY.keys())
            raise LucisEngineError(
                engine_name=engine,
                detail=f"Unknown engine '{engine}'. Available: {available}"
            )
        self.engine = engine_class(storage=self.storage)

        # 3. Smart persistence: if the index already exists on disk, load it
        # This enables the "pick up where you left off" workflow:
        #   cp = Lucis(name="my_index")  →  ready to search immediately
        if autoload and self.storage.exists(name):
            self.load()

    # factory methods
    @classmethod
    def from_dict(
        cls, 
        data: Dict[Any, str], 
        name: str = "default", 
        **kwargs
    ) -> "Lucis":
        """
        Creates a Lucis instance from a dictionary {id: text}.
        
        Preserves original keys as document IDs in search results.
        This is the recommended format when you have meaningful IDs
        (e.g., database PKs, document codes, email addresses).

        Args:
            data: Dictionary mapping document IDs to their text content.
            name: Identifier for persistence.
            **kwargs: Additional arguments passed to __init__ (storage_dir, engine, etc.)

        Returns:
            A ready-to-search Lucis instance.

        Example:
            cp = Lucis.from_dict({
                "doc_001": "Python es un lenguaje versátil",
                "doc_002": "El amor por la programación crece cada día"
            })
            results = cp.search("programación python")
        """
        # autoload=False to avoid loading stale data before indexing fresh data
        instance = cls(name=name, autoload=False, **kwargs)
        instance.index(data)
        return instance

    @classmethod
    def from_list(
        cls, 
        data: List[str], 
        name: str = "default", 
        **kwargs
    ) -> "Lucis":
        """
        Creates a Lucis instance from a list of text documents.
        
        Document IDs will be auto-generated as sequential integers (0, 1, 2...).
        This is the simplest way to get started when IDs don't matter.

        Args:
            data: List of text documents.
            name: Identifier for persistence.
            **kwargs: Additional arguments passed to __init__ (storage_dir, engine, etc.)

        Returns:
            A ready-to-search Lucis instance.

        Example:
            cp = Lucis.from_list([
                "Python es un lenguaje versátil",
                "El amor por la programación crece cada día"
            ])
            results = cp.search("programación")
        """
        instance = cls(name=name, autoload=False, **kwargs)
        instance.index(data)
        return instance

    # core methods
    def index(self, data: Union[List[str], Dict[Any, str]], persist: bool = True) -> None:
        """
        The "all-terrain" ingestion method.
        
        Detects whether data is a Dict or List and delegates to the engine.
        This is the single entry point for all data ingestion — the engine's
        _normalize_corpus handles the rest.

        Args:
            data: Either a Dict[id, text] or List[text] to index.
            persist: Whether to save the index to storage after building.
        """
        self.engine.build_index(data)
        self._is_indexed = True
        if persist:
            self.save()

    def search(self, query: Union[str, List[str]], top_k: int = 10) -> SearchResponse:
        """
        Searches the indexed corpus for documents matching the query.

        The engine returns raw tuples; Lucis wraps them in a SearchResponse
        with full context: query, tokens, timing, and structured results.

        Args:
            query: A search string ("amor python") or pre-tokenized list (["amor", "python"]).
            top_k: Maximum number of results to return.

        Returns:
            SearchResponse with ranked results and search metadata.

        Example:
            response = cp.search("programación python", top_k=5)
            print(response.total_results)        # 5
            print(response.results[0].doc_id)     # "doc_001"
            print(response.results[0].score)      # 0.3903
            print(response.search_time_ms)        # 2.31
            print(response.to_dict())             # JSON-ready dict
        """
        if not self._is_indexed:
            raise LucisEngineError(
                engine_name=self.engine.name,
                detail="No index built yet. Use .index(data), .from_dict(), or .from_list() first."
            )

        # Preserve the original query before tokenization
        original_query = query

        # Tokenize here to capture the tokens for the response
        # (The engine's decorator will see it's already tokenized and pass through)
        if isinstance(query, str):
            from .utils.nlp import word_tokenizer
            tokens = word_tokenizer(query)
        else:
            tokens = list(query)

        # Time the engine search (the core computation)
        start = time.perf_counter()
        raw_results = self.engine.search(tokens, top_k=top_k)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Wrap raw tuples into structured SearchResult objects
        results = [
            SearchResult(doc_id=doc_id, score=round(score, 6), rank=rank)
            for rank, (doc_id, score) in enumerate(raw_results, start=1)
        ]

        return SearchResponse(
            query=original_query,
            tokens=tokens,
            engine=self.engine.name,
            total_results=len(results),
            search_time_ms=round(elapsed_ms, 2),
            results=results,
        )

    # persistence methods
    def save(self, name: Optional[str] = None) -> None:
        """
        Persists the current index to storage.
        
        Uses self.name by default, or a custom name if provided.
        This allows "save as" functionality: cp.save("backup_v2")

        Args:
            name: Optional custom name. Falls back to self.name.
        """
        save_name = name or self.name
        self.engine.persist(save_name)

    def load(self, name: Optional[str] = None) -> None:
        """
        Loads a previously saved index from storage.

        Args:
            name: Optional custom name. Falls back to self.name.
        """
        load_name = name or self.name
        self.engine.load_engine(load_name)
        self._is_indexed = True
    
    # info and debugging
    def __repr__(self) -> str:
        status = "indexed" if self._is_indexed else "empty"
        docs = self.engine.total_docs if self._is_indexed else 0
        id_t = self.engine.id_type if self._is_indexed else "N/A"
        return f"Lucis(name='{self.name}', engine='{self.engine.name}', docs={docs}, idx_type='{id_t}', status='{status}')"