
import pytest
from yeny.utils.decorators import corpus_input, doc_input
from yeny.exceptions import YenyInvalidDocumentError

def simple_tokenizer(text):
    return text.lower().split()

def dummy_processor(corpus):
    return {"processed": corpus}

def dummy_search(query):
    return {"query": query, "results": []}

class DummyClass:
    
    @doc_input(simple_tokenizer)
    def search_method(self, query):
        return {"query": query, "type": "method"}
    
    @corpus_input(simple_tokenizer)
    def index_method(self, corpus):
        return {"corpus": corpus, "type": "method"}

class TestCorpusInput:

    def test_corpus_strings_tokeniza(self):
        @corpus_input(simple_tokenizer)
        def process_corpus(corpus):
            return corpus
        
        result = process_corpus(["Hola Mundo", "Python Testing"])
        assert result == [["hola", "mundo"], ["python", "testing"]]

    def test_corpus_lists_pasa_without_cambios(self):
        @corpus_input(simple_tokenizer)
        def process_corpus(corpus):
            return corpus
        
        input_corpus = [["hola", "mundo"], ["python", "testing"]]
        result = process_corpus(input_corpus)
        assert result == input_corpus

    def test_corpus_empty(self):
        @corpus_input(simple_tokenizer)
        def process_corpus(corpus):
            return corpus
        
        result = process_corpus([])
        assert result == []

    def test_tokenizer_se_aplica_correctly(self):
        @corpus_input(simple_tokenizer)
        def process_corpus(corpus):
            return corpus
        
        result = process_corpus(["UPPERCASE TEXT"])
        assert result == [["uppercase", "text"]]

    def test_integracion_with_function_decorada(self):
        @corpus_input(simple_tokenizer)
        def my_indexer(corpus):
            return {"indexed": len(corpus), "docs": corpus}
        
        result = my_indexer(["Doc one", "Doc two", "Doc three"])
        assert result["indexed"] == 3
        assert result["docs"] == [["doc", "one"], ["doc", "two"], ["doc", "three"]]

    def test_resultado_se_returns_correctly(self):
        @corpus_input(simple_tokenizer)
        def my_indexer(corpus):
            return {"status": "ok", "count": len(corpus)}
        
        result = my_indexer(["Doc one", "Doc two"])
        assert result == {"status": "ok", "count": 2}

    def test_multiple_documents(self):
        @corpus_input(simple_tokenizer)
        def process(corpus):
            return corpus
        
        docs = ["First document", "Second document", "Third document"]
        result = process(docs)
        assert len(result) == 3
        assert all(isinstance(doc, list) for doc in result)
        assert result[0] == ["first", "document"]

class TestDocInput:

    def test_tokeniza_string_correctly(self):
        @doc_input(simple_tokenizer)
        def search_func(query):
            return query
        
        result = search_func("Python Testing")
        assert result == ["python", "testing"]

    def test_pasa_tokenizado_a_function(self):
        @doc_input(simple_tokenizer)
        def search_func(query):
            return {"tokens": query}
        
        result = search_func("Python Testing")
        assert result == {"tokens": ["python", "testing"]}

    def test_list_not_se_tokeniza_again(self):
        @doc_input(simple_tokenizer)
        def search_func(query):
            return query
        
        tokens = ["python", "testing"]
        result = search_func(tokens)
        assert result == tokens

    def test_list_pasa_directamente(self):
        @doc_input(simple_tokenizer)
        def search_func(query):
            return {"tokens": query, "count": len(query)}
        
        tokens = ["python", "testing", "unit"]
        result = search_func(tokens)
        assert result == {"tokens": tokens, "count": 3}

    def test_list_vacia_pasa_without_cambios(self):
        @doc_input(simple_tokenizer)
        def search_func(query):
            return query
        
        result = search_func([])
        assert result == []

    def test_method_instancia_querand_index_1(self):
        obj = DummyClass()
        result = obj.search_method("Python Testing")
        assert result["query"] == ["python", "testing"]
        assert result["type"] == "method"

    def test_function_standalone_querand_index_0(self):
        @doc_input(simple_tokenizer)
        def search_func(query):
            return query
        
        result = search_func("Python Testing")
        assert result == ["python", "testing"]

    def test_method_instancia_varios_args(self):
        class TestClass:
            @doc_input(simple_tokenizer)
            def search(self, query, top_k=10):
                return {"query": query, "top_k": top_k}
        
        obj = TestClass()
        result = obj.search("Python Testing", top_k=5)
        assert result["query"] == ["python", "testing"]
        assert result["top_k"] == 5

    def test_querand_not_str_ni_list_error(self):
        @doc_input(simple_tokenizer)
        def search_func(query):
            return query
        
        with pytest.raises(YenyInvalidDocumentError):
            search_func(123)

    def test_list_with_elements_not_str(self):
        @doc_input(simple_tokenizer)
        def search_func(query):
            return query
        
        with pytest.raises(YenyInvalidDocumentError):
            search_func([123])

    def test_querand_none_error(self):
        @doc_input(simple_tokenizer)
        def search_func(query):
            return query
        
        with pytest.raises(YenyInvalidDocumentError):
            search_func(None)

    def test_querand_dict_error(self):
        @doc_input(simple_tokenizer)
        def search_func(query):
            return query
        
        with pytest.raises(YenyInvalidDocumentError):
            search_func({"key": "value"})

class TestDocInputIntegration:

    def test_preserves_otros_args(self):
        @doc_input(simple_tokenizer)
        def search_func(query, threshold=0.5, max_results=10):
            return {
                "tokens": query,
                "threshold": threshold,
                "max_results": max_results
            }
        
        result = search_func("Python Testing", threshold=0.8, max_results=5)
        assert result["tokens"] == ["python", "testing"]
        assert result["threshold"] == 0.8
        assert result["max_results"] == 5

    def test_kwargs_worksn(self):
        @doc_input(simple_tokenizer)
        def search_func(query, **kwargs):
            return {"query": query, "kwargs": kwargs}
        
        result = search_func("Python Testing", top_k=5, mode="fast")
        assert result["query"] == ["python", "testing"]
        assert result["kwargs"] == {"top_k": 5, "mode": "fast"}

    def test_method_with_attributes_instancia(self):
        class SearchEngine:
            def __init__(self, name):
                self.name = name
                self.tokenizer = simple_tokenizer
            
            @doc_input(simple_tokenizer)
            def search(self, query):
                return {"engine": self.name, "tokens": query}
        
        engine = SearchEngine("test_engine")
        result = engine.search("Python Testing")
        assert result["engine"] == "test_engine"
        assert result["tokens"] == ["python", "testing"]

    def test_string_case_insensitive(self):
        @doc_input(simple_tokenizer)
        def search_func(query):
            return query
        
        result = search_func("PYTHON TESTING")
        assert result == ["python", "testing"]

    def test_string_with_punctuation(self):
        @doc_input(simple_tokenizer)
        def search_func(query):
            return query
        
        result = search_func("Python, Testing!")
        assert "python," in result
        assert "testing!" in result

    def test_string_empty(self):
        @doc_input(simple_tokenizer)
        def search_func(query):
            return query
        
        result = search_func("")
        assert result == []

    def test_string_with_spaces_multiple(self):
        @doc_input(simple_tokenizer)
        def search_func(query):
            return query
        
        result = search_func("Python   Testing")
        assert result == ["python", "testing"]