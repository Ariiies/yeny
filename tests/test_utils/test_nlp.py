
import pytest
from lucis.utils.nlp import (
    simple_tokenizer,
    word_tokenizer,
    ngram_tokenizer,
    char_ngram_tokenizer,
    lowercase,
    uppercase,
    strip_whitespace,
    remove_punctuation,
    remove_numbers,
    remove_extra_spaces,
    remove_urls,
    remove_emails,
    remove_html_tags,
    normalize_unicode,
    remove_accents,
)

class TestSimpleTokenizer:

    def test_split_basic(self):
        assert simple_tokenizer("hello world") == ["hello", "world"]

    def test_text_empty(self):
        assert simple_tokenizer("") == []

    def test_withoutgle_token(self):
        assert simple_tokenizer("python") == ["python"]

    def test_multiple_spaces(self):
        assert simple_tokenizer("hello   world") == ["hello", "world"]

    def test_tabs_and_newlines(self):
        result = simple_tokenizer("hello\tworld\npython")
        assert result == ["hello", "world", "python"]

class TestWordTokenizer:

    def test_onland_words(self):
        assert word_tokenizer("Python 3.9 is awesome!") == ["python", "is", "awesome"]

    def test_ignores_numbers(self):
        assert word_tokenizer("version 3.9") == ["version"]
        assert "3" not in word_tokenizer("i have 3 dogs")
        assert "9" not in word_tokenizer("i have 3.9 dogs")

    def test_withverts_a_lowercase(self):
        assert word_tokenizer("PYTHON IS AWESOME") == ["python", "is", "awesome"]

    def test_special_characters(self):
        assert word_tokenizer("hello!!! world???") == ["hello", "world"]
        assert word_tokenizer("price: $100") == ["price"]

    def test_spanish_accented_characters(self):
        assert word_tokenizer("cancion nino") == ["cancion", "nino"]
        assert word_tokenizer("penguin") == ["penguin"]
        assert word_tokenizer("light year") == ["light", "year"]

    def test_text_empty(self):
        assert word_tokenizer("") == []

    def test_onland_punctuation(self):
        assert word_tokenizer("!!! ??? ...") == []

    def test_mix_words_numbers_punctuation(self):
        result = word_tokenizer("Python 3.9, JavaScript; TypeScript!")
        assert result == ["python", "javascript", "typescript"]
        assert "3" not in result
        assert "9" not in result

class TestNgramTokenizer:

    def test_factorand_nombre(self):
        bigram = ngram_tokenizer(2)
        assert bigram.__name__ == "ngram_2_tokenizer"

    def test_bigrams(self):
        bigram = ngram_tokenizer(2)
        result = bigram("hello world cruel")
        assert result == ["hello world", "world cruel"]

    def test_trigrams(self):
        trigram = ngram_tokenizer(3)
        result = trigram("hello world cruel python")
        assert result == ["hello world cruel", "world cruel python"]

    def test_less_words_que_n(self):
        bigram = ngram_tokenizer(2)
        assert bigram("hello") == ["hello"]
        assert bigram("") == []

    def test_text_empty(self):
        bigram = ngram_tokenizer(2)
        assert bigram("") == []

    def test_spaces_multiple(self):
        bigram = ngram_tokenizer(2)
        result = bigram("hello   world")
        assert result == ["hello world"]

    def test_withoutgle_token(self):
        bigram = ngram_tokenizer(2)
        assert bigram("python") == ["python"]

class TestCharNgramTokenizer:

    def test_factorand_nombre(self):
        tokenizer = char_ngram_tokenizer(3)
        assert tokenizer.__name__ == "char_3gram_tokenizer"

    def test_default_trigrams(self):
        tokenizer = char_ngram_tokenizer()
        result = tokenizer("python")
        assert result == ["pyt", "yth", "tho", "hon"]

    def test_bigrams(self):
        tokenizer = char_ngram_tokenizer(2)
        result = tokenizer("hello")
        assert result == ["he", "el", "ll", "lo"]

    def test_replaces_spaces(self):
        tokenizer = char_ngram_tokenizer(3)
        result = tokenizer("hello world")
        assert " " not in result
        assert any("_" in ngram for ngram in result)

    def test_withverts_a_lowercase(self):
        tokenizer = char_ngram_tokenizer(2)
        result = tokenizer("PYTHON")
        assert result == ["py", "yt", "th", "ho", "on"]

    def test_text_short_menor_que_n(self):
        tokenizer = char_ngram_tokenizer(5)
        assert tokenizer("hello") == ["hello"]

    def test_text_empty(self):
        tokenizer = char_ngram_tokenizer(3)
        assert tokenizer("") == []

    def test_length_exacta_n(self):
        tokenizer = char_ngram_tokenizer(3)
        assert tokenizer("abc") == ["abc"]

    def test_special_characters(self):
        tokenizer = char_ngram_tokenizer(2)
        result = tokenizer("a!b")
        assert result == ["a!", "!b"]

class TestLowercase:

    def test_withverts_a_lowercase(self):
        assert lowercase("PYTHON") == "python"
        assert lowercase("HeLLo WoRLd") == "hello world"

    def test_keeps_numbers(self):
        assert lowercase("Python 3.9") == "python 3.9"

    def test_keeps_simbolos(self):
        assert lowercase("HELLO!") == "hello!"

    def test_characters_unicode(self):
        assert lowercase("CAFÉ") == "café"
        assert lowercase("NAÏVE") == "naïve"

class TestUppercase:

    def test_withverts_a_uppercase(self):
        assert uppercase("python") == "PYTHON"
        assert uppercase("hello world") == "HELLO WORLD"

    def test_keeps_numbers(self):
        assert uppercase("python 3.9") == "PYTHON 3.9"

    def test_keeps_simbolos(self):
        assert uppercase("hello!") == "HELLO!"

class TestStripWhitespace:

    def test_removes_spaces_inicio_final(self):
        assert strip_whitespace("  hello  ") == "hello"

    def test_normalizes_multiple_spaces(self):
        assert strip_whitespace("hello   world") == "hello world"

    def test_tabs_and_newlines(self):
        assert strip_whitespace("hello\tworld\npython") == "hello world python"

    def test_without_spaces_extra(self):
        assert strip_whitespace("hello world") == "hello world"

    def test_text_empty(self):
        assert strip_whitespace("") == ""

    def test_onland_spaces(self):
        assert strip_whitespace("   ") == ""

class TestRemovePunctuation:

    def test_removes_punctuation_basica(self):
        result = remove_punctuation("Hello, world!")
        assert result == "Hello world"

    def test_keeps_punctuation_keep(self):
        result = remove_punctuation("Hello, world!", keep=",")
        assert result == "Hello, world"

    def test_punctuation_spanisha(self):
        result = remove_punctuation("Hello! How are you?")
        assert result == "Hello How are you"

    def test_text_without_punctuation(self):
        assert remove_punctuation("hello world") == "hello world"

    def test_text_empty(self):
        assert remove_punctuation("") == ""

    def test_keeps_numbers(self):
        assert remove_punctuation("version 3.9") == "version 39"

class TestRemoveNumbers:

    def test_removes_digits(self):
        assert remove_numbers("Python 3.9") == "Python ."

    def test_multiple_numbers(self):
        assert remove_numbers("123 456 789") == "  "

    def test_without_numbers(self):
        assert remove_numbers("hello world") == "hello world"

    def test_numbers_en_words(self):
        assert remove_numbers("python3") == "python"

class TestRemoveExtraSpaces:

    def test_multiple_spaces(self):
        assert remove_extra_spaces("hello   world") == "hello world"

    def test_tabs_and_newlines(self):
        assert remove_extra_spaces("hello\tworld\npython") == "hello world python"

    def test_strip_final(self):
        assert remove_extra_spaces("  hello world  ") == "hello world"

    def test_without_spaces_extra(self):
        assert remove_extra_spaces("hello world") == "hello world"

class TestRemoveUrls:

    def test_url_http(self):
        assert remove_urls("Visit http://example.com") == "Visit "

    def test_url_https(self):
        assert remove_urls("Visit https://example.com") == "Visit "

    def test_url_www(self):
        assert remove_urls("Visit www.example.com") == "Visit "

    def test_without_urls(self):
        assert remove_urls("hello world") == "hello world"

    def test_url_with_path(self):
        result = remove_urls("Check https://example.com/path/to/page")
        assert "https" not in result
        assert "example.com" not in result

class TestRemoveEmails:

    def test_email_standard(self):
        result = remove_emails("Contact: user@example.com")
        assert result == "Contact: "

    def test_email_with_puntos(self):
        result = remove_emails("Contact: john.doe@example.com")
        assert result == "Contact: "

    def test_without_emails(self):
        assert remove_emails("hello world") == "hello world"

    def test_multiple_emails(self):
        result = remove_emails("a@a.com and b@b.com")
        assert "@" not in result
        assert ".com" not in result

class TestRemoveHtmlTags:

    def test_tag_simple(self):
        assert remove_html_tags("<p>hello</p>") == "hello"
        assert remove_html_tags("<div>world</div>") == "world"

    def test_tag_with_attributes(self):
        result = remove_html_tags('<a href="http://example.com">link</a>')
        assert result == "link"

    def test_multiple_tags(self):
        result = remove_html_tags("<p>hello</p><div>world</div>")
        assert result == "helloworld"

    def test_without_tags(self):
        assert remove_html_tags("hello world") == "hello world"

    def test_tag_nested(self):
        result = remove_html_tags("<div><p>hello</p></div>")
        assert result == "hello"

class TestNormalizeUnicode:

    def test_removes_accents(self):
        assert normalize_unicode("café") == "cafe"
        assert normalize_unicode("naïve") == "naive"
        assert normalize_unicode("touché") == "touche"

    def test_characters_without_accent(self):
        assert normalize_unicode("python") == "python"
        assert normalize_unicode("123") == "123"

    def test_text_empty(self):
        assert normalize_unicode("") == ""

    def test_mix(self):
        result = normalize_unicode("résumé and python")
        assert result == "resume and python"

class TestRemoveAccents:

    def test_es_alias(self):
        text = "café naïve"
        assert remove_accents(text) == normalize_unicode(text)

    def test_works_as_normalize(self):
        assert remove_accents("café") == "cafe"
        assert remove_accents("naïve") == "naive"