from collections import defaultdict
from ..decorators import corpus_input, doc_input
from ..nlp import word_tokenizer, simple_tokenizer
from typing import List, Dict, Set

# Build index function, pure Python implementation
@corpus_input(word_tokenizer)
def build_index(
     tokenized_corpus: List[List[str]],
     as_pure_dict: bool = False # Convert to normal dicts if True, it happens in the decorator
     ) -> dict[str, dict[int, int]]:
        """
        Builds index (inverted ways) in a single pass O(n).
        
        Example:
            corpus = [["hello", "world", "hello"], ["python", "world"]]
            result = {
                "hello": {0: 2},      # "hello" appears 2 times in doc 0
                "world": {0: 1, 1: 1}, # "world" appears 1 time in doc 0 and 1
                "python": {1: 1}      # "python" appears 1 time in doc 1
            }
        """
        # Using defaultdict for automatic initialization is the most efficient way in pure Python.
        # When index recives an word not seen before, it creates a new defaultdict for it, if exists, it uses the existing one and increments the count.
        # The lambda function acts as a 'factory' to create these nested dictionaries, where 'i' (document index) becomes the key for frequency counting.
        index: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
        
        for i, docs in enumerate(tokenized_corpus):
            for word in docs:
                index[word][i] += 1
        # reminder: accessing to a word with .get(word, {}) will return an empty dict if word not in index
        # this void dirting the rest of dict creating unnecessary empty keys --  to see a normal dict use = {k : dict(v) for k, v in index.items()}
        return index


@doc_input(word_tokenizer)
def get_bow(tokens: List[str]) -> Dict[str, int]:
    """
    generates a Bag of Words for a single document.
    """
    bow = {}
    for token in tokens:
        bow[token] = bow.get(token, 0) + 1
    return bow

@corpus_input(word_tokenizer)
def get_corpus_bows(corpus: List[List[str]]) -> List[Dict[str, int]]:
    """
    generates Bag of Words for an entire corpus.
    """
    return [get_bow(doc) for doc in corpus]

@corpus_input(word_tokenizer)
def get_vocabulary(corpus: List[List[str]]) -> List[str]:
    """
    extracts the unique and sorted vocabulary from the entire corpus.
    Essential for dense vector operations (NumPy).
    """
    vocab: Set[str] = set()
    for doc in corpus:
        vocab.update(doc)
    return sorted(list(vocab))