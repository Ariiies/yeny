import re

"""
Basic text cleaners.
"""

def lowercase(text: str) -> str:
    """Converts text to lowercase."""
    return text.lower()


def uppercase(text: str) -> str:
    """Converts text to uppercase."""
    return text.upper()


def strip_whitespace(text: str) -> str:
    """Removes leading and trailing spaces, normalizes multiple spaces."""
    return ' '.join(text.split())


def remove_punctuation(text: str, keep: str = "") -> str:
    """
    Removes punctuation from text (including Spanish punctuation marks).
    
    Args:
        text: Text to clean
        keep: Punctuation characters to keep (e.g., ".,")
    """
    import string
    # Include Spanish punctuation marks
    spanish_punct = "¡¿"
    all_punct = string.punctuation + spanish_punct
    chars_to_remove = ''.join(c for c in all_punct if c not in keep)
    translator = str.maketrans('', '', chars_to_remove)
    return text.translate(translator)


def remove_numbers(text: str) -> str:
    """Removes all digits from the text."""
    return re.sub(r'\d+', '', text)


def remove_extra_spaces(text: str) -> str:
    """Replaces multiple spaces with a single space."""
    return re.sub(r'\s+', ' ', text).strip()


def remove_urls(text: str) -> str:
    """Removes URLs from the text."""
    url_pattern = r'https?://\S+|www\.\S+'
    return re.sub(url_pattern, '', text)


def remove_emails(text: str) -> str:
    """Removes email addresses from the text."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.sub(email_pattern, '', text)


def remove_html_tags(text: str) -> str:
    """Removes HTML tags from the text."""
    return re.sub(r'<[^>]+>', '', text)


def normalize_unicode(text: str) -> str:
    """
    Normalizes unicode characters (e.g., café -> cafe).
    
    Useful for searches where accents don't matter.
    """
    import unicodedata
    normalized = unicodedata.normalize('NFD', text)
    return ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')


def remove_accents(text: str) -> str:
    """Alias for normalize_unicode - removes accents."""
    return normalize_unicode(text)