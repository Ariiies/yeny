import re


class SimpleTokenizer:
    """Simple tokenizer: splits by spaces."""
    def __call__(self, text: str)->list[str]:
        return text.split()

class WordTokenizer:
    def __call__(self, text: str)->list[str]:
        """Tokenizer that extracts only words (ignores standalone numbers)."""
        return re.findall(r'\b[a-záéíóúüñ]+\b', text.lower())


"""
Class for word n-gram tokenizer.
Example:
    bigram = ngram_tokenizer(2)
    bigram("Hello world cruel")  # ["Hello world", "world cruel"]
"""
class NgramTokenizer:
    def __init__(self, n:int = 2):
        if n <=0:
            raise ValueError("n must be greater than 0")
        self.n: int = n

    def __repr__(self)-> str:
        return f"ngram_{self.n}_tokenizer"

    def __call__(self, text: str)-> list[str]:
        words = text.split()
        if len(words) < self.n:
            return []
        return [' '.join(words[i:i+self.n]) for i in range(len(words) - self.n + 1)]


"""
Class for character n-gram tokenizer.    
Useful for fuzzy search and language detection.
"""
class CharNgramTokenizer:
    def __init__(self, n: int = 3):
        if n <=0:
            raise ValueError("n must be greater than 0")
        self.n: int = n

    def __repr__(self)-> str:
        return f"char_{self.n}gram_tokenizer"

    def __call__(self, text: str)->list[str]:
        if len(text) < self.n:
            return []
        return [text[i:i+self.n].lower() for i in range(len(text)-(self.n-1))]