from collections import defaultdict, Counter
import array
from ..decorators import corpus_input, doc_input
from ..nlp import WordTokenizer
from typing import List, Dict, Set
from ..compact import CompactPostings


# Build index function, pure Python implementation
@corpus_input(WordTokenizer())
def build_index(tokenized_corpus: List[List[str]]) -> Dict[str, CompactPostings]:
        """
        Builds a compact inverted index in a single pass O(n).

        Returns ``Dict[str, CompactPostings]`` — memory-efficient posting
        lists backed by ``array.array``.  For a human-readable view use
        ``postings.to_dict()`` on any entry::

            idx = build_index(corpus)
            print(idx["hello"].to_dict())   # {0: 2}

        Example (logical representation)::

            corpus = [["hello", "world", "hello"], ["python", "world"]]
             result (compact, equivalent to):
               "hello"  => {0: 2}
               "world"  => {0: 1, 1: 1}
               "python" => {1: 1}
        """
        docs: dict[str, array.array] = defaultdict(lambda: array.array("I"))
        frequency: dict[str, array.array] = defaultdict(lambda: array.array("I"))

        for doc_id, tokens in enumerate(tokenized_corpus):
            for word, freq in Counter(tokens).items(): docs[word].append(doc_id), frequency[word].append(freq)

        return {word: CompactPostings(docs[word], frequency[word]) for word in docs}


@doc_input(WordTokenizer())
def get_bow(tokens: List[str]) -> Dict[str, int]:
    """
    generates a Bag of Words for a single document.
    """
    bow = {}
    for token in tokens: bow[token] = bow.get(token, 0) + 1
    return bow

@corpus_input(WordTokenizer())
def get_corpus_bows(corpus: List[List[str]]) -> List[Dict[str, int]]:
    """
    generates Bag of Words for an entire corpus.
    """
    return [get_bow(doc) for doc in corpus]

@corpus_input(WordTokenizer())
def get_vocabulary(corpus: List[List[str]]) -> List[str]:
    """
    extracts the unique and sorted vocabulary from the entire corpus.
    Essential for dense vector operations (NumPy).
    """
    vocab: Set[str] = set()
    for doc in corpus: vocab.update(doc)
    return sorted(list(vocab))