import functools
from typing import Callable, List, Union, Any
from ..exceptions import LucisInvalidDocumentError

# input corpus tokenizer helper decorator
def corpus_input(tokenizer: Callable[[str], List[str]]):
    """
    Decorator that manages the index creation lifecycle.
    
    Handles three phases:
    1. Pre-processing: Tokenizes raw strings if needed.
    2. Execution: Calls the actual indexing logic.
    3. Post-processing: Converts defaultdict to pure dict if requested.
    
    This allows index functions to focus only on their core logic,
    while the decorator handles input normalization and output formatting.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(corpus: Union[List[str], List[List[str]]], *args, **kwargs) -> Any:
            # Check if corpus contains raw strings (not yet tokenized)
            # Using corpus[0] check is O(1) - we assume homogeneous input
            if corpus and isinstance(corpus[0], str):
                # Apply injected tokenizer - this decouples tokenization strategy from indexing logic
                corpus = [tokenizer(doc) for doc in corpus]

            # Call the wrapped function with processed corpus
            return func(corpus, *args, **kwargs)
        return wrapper
    return decorator


## input document/query tokenizer helper decorator
def doc_input(tokenizer: Callable[[str], List[str]]):
    """
    Decorator that manages the input query/docs for a search or bow creating.
    
    Handles three phases:
    1. Pre-processing: Tokenizes raw strings if needed.
    2. Execution: Calls the actual indexing logic.

    This allows search functions to focus only on their core logic,
    while the decorator handles input normalization.
    
    Works with both instance methods (with self) and standalone functions.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            args_list = list(args)
            
            # Determine the index of the query/data argument
            # If first arg looks like an instance (has __dict__ and is not a str/list), 
            # query is at index 1, otherwise at index 0
            if args_list and hasattr(args_list[0], '__dict__') and not isinstance(args_list[0], (str, list)):
                # It's an instance method, query is at index 1
                query_index = 1
            else:
                # It's a standalone function, query is at index 0
                query_index = 0
            
            if query_index >= len(args_list):
                raise LucisInvalidDocumentError(detail="No query argument provided.")
            
            query = args_list[query_index]
            
            # Tokenize if needed
            if isinstance(query, str):
                # Single string - tokenize it
                args_list[query_index] = tokenizer(query)
            elif isinstance(query, list) and query and isinstance(query[0], str):
                # Already a list of strings (tokens) - no action needed
                pass
            elif isinstance(query, list) and not query:
                # Empty list - pass through
                pass
            else:
                raise LucisInvalidDocumentError(detail="Query must be a string or a list of strings.")
            
            # Call the wrapped function with processed arguments
            result = func(*args_list, **kwargs)
            
            return result
        return wrapper
    return decorator