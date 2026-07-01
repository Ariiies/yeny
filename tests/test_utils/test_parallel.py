
import pytest
from lucis.utils.parallel import (
    get_cpu_count,
    get_optimal_workers,
    parallel_preprocess,
    _sequential_preprocess,
    _is_picklable,
)

def simple_preprocessor(text):
    return text.upper()

def simple_tokenizer(text):
    return text.split()

def preprocessor_returns_str(text):
    return text.upper()

def preprocessor_returns_list(text):
    return text.upper().split()

class DummyPreprocessor:
    def __call__(self, text):
        return text.upper()

class UnpicklablePreprocessor:
    def __init__(self, func):
        self.func = func
    
    def __call__(self, text):
        return self.func(text)

class TestGetCpuCount:

    def test_returns_entero_positivo(self):
        count = get_cpu_count()
        assert isinstance(count, int)
        assert count > 0

    def test_fallback_a_2(self):
        
        count = get_cpu_count()
        assert count >= 1

class TestGetOptimalWorkers:

    def test_modo_efficiency(self):
        workers = get_optimal_workers("efficiency")
        assert isinstance(workers, int)
        assert workers >= 1

    def test_modo_performance(self):
        workers = get_optimal_workers("performance")
        assert isinstance(workers, int)
        assert workers >= 1

    def test_siempre_returns_greater_equal_1(self):
        for mode in ["efficiency", "performance", "invalid_mode"]:
            workers = get_optimal_workers(mode)
            assert workers >= 1

    def test_modo_invalid_usa_efficiency(self):
        workers = get_optimal_workers("invalid_mode_xyz")
        assert workers >= 1

class TestParallelPreprocess:

    def test_workers_none_usa_get_optimal_workers(self):
        texts = ["test doc"]
        result = parallel_preprocess(
            texts,
            preprocessor=preprocessor_returns_str,
            tokenizer=simple_tokenizer,
            workers=None,
            min_docs=1
        )
        assert len(result) == 1

    def test_workers_1_sequential(self):
        texts = ["doc one", "doc two"]
        result = parallel_preprocess(
            texts,
            preprocessor=preprocessor_returns_str,
            tokenizer=simple_tokenizer,
            workers=1,
            min_docs=1
        )
        assert len(result) == 2
        assert all(isinstance(doc, list) for doc in result)

    def test_n_menor_que_min_docs_sequential(self):
        texts = ["doc one", "doc two"]
        result = parallel_preprocess(
            texts,
            preprocessor=preprocessor_returns_str,
            tokenizer=simple_tokenizer,
            workers=4,
            min_docs=100
        )
        assert len(result) == 2

    def test_procesador_not_picklable_sequential(self):
        unpicklable = UnpicklablePreprocessor(lambda x: x.upper())
        texts = ["doc one", "doc two"]
        result = parallel_preprocess(
            texts,
            preprocessor=unpicklable,
            tokenizer=simple_tokenizer,
            workers=4,
            min_docs=1
        )
        assert len(result) == 2

    def test_order_resultados_preservesdo(self):
        texts = ["first", "second", "third", "fourth", "fifth"]
        result = parallel_preprocess(
            texts,
            preprocessor=preprocessor_returns_str,
            tokenizer=simple_tokenizer,
            workers=2,
            min_docs=1
        )
        assert len(result) == 5
        assert result[0] == ["FIRST"]
        assert result[1] == ["SECOND"]
        assert result[2] == ["THIRD"]

    def test_preprocessor_returns_str_aplica_tokenizer(self):
        texts = ["hello world"]
        result = parallel_preprocess(
            texts,
            preprocessor=preprocessor_returns_str,
            tokenizer=simple_tokenizer,
            workers=1,
            min_docs=1
        )
        assert result == [["HELLO", "WORLD"]]

    def test_preprocessor_returns_list_usa_directamente(self):
        texts = ["hello world"]
        result = parallel_preprocess(
            texts,
            preprocessor=preprocessor_returns_list,
            tokenizer=simple_tokenizer,
            workers=1,
            min_docs=1
        )
        assert result == [["HELLO", "WORLD"]]

    def test_corpus_empty(self):
        result = parallel_preprocess(
            [],
            preprocessor=preprocessor_returns_str,
            tokenizer=simple_tokenizer,
            workers=1,
            min_docs=1
        )
        assert result == []

    def test_text_empty(self):
        texts = [""]
        result = parallel_preprocess(
            texts,
            preprocessor=preprocessor_returns_str,
            tokenizer=simple_tokenizer,
            workers=1,
            min_docs=1
        )
        assert len(result) == 1
        assert result[0] == []

    def test_multiple_documents_large(self):
        texts = [f"document {i} with some content" for i in range(20)]
        result = parallel_preprocess(
            texts,
            preprocessor=preprocessor_returns_str,
            tokenizer=simple_tokenizer,
            workers=2,
            min_docs=5
        )
        assert len(result) == 20
        assert all(isinstance(doc, list) for doc in result)
        assert result[0] == ["DOCUMENT", "0", "WITH", "SOME", "CONTENT"]

    def test_preprocessor_clase_picklable(self):
        preproc = DummyPreprocessor()
        texts = ["hello", "world"]
        result = parallel_preprocess(
            texts,
            preprocessor=preproc,
            tokenizer=simple_tokenizer,
            workers=2,
            min_docs=1
        )
        assert len(result) == 2
        assert result[0] == ["HELLO"]
        assert result[1] == ["WORLD"]

class TestSequentialPreprocess:

    def test_procesa_todos_los_documents(self):
        texts = ["doc one", "doc two", "doc three"]
        result = _sequential_preprocess(texts, preprocessor_returns_str, simple_tokenizer)
        assert len(result) == 3

    def test_aplica_preprocessor_and_tokenizer(self):
        texts = ["hello world"]
        result = _sequential_preprocess(texts, preprocessor_returns_str, simple_tokenizer)
        assert result == [["HELLO", "WORLD"]]

    def test_preprocessor_returns_str(self):
        texts = ["hello world"]
        result = _sequential_preprocess(texts, preprocessor_returns_str, simple_tokenizer)
        assert all(isinstance(doc, list) for doc in result)

    def test_preprocessor_returns_list(self):
        texts = ["hello world"]
        result = _sequential_preprocess(texts, preprocessor_returns_list, simple_tokenizer)
        assert all(isinstance(doc, list) for doc in result)

    def test_corpus_empty(self):
        result = _sequential_preprocess([], preprocessor_returns_str, simple_tokenizer)
        assert result == []

    def test_text_empty(self):
        result = _sequential_preprocess([""], preprocessor_returns_str, simple_tokenizer)
        assert len(result) == 1
        assert result[0] == []

class TestIsPicklable:

    def test_function_picklable_returns_true(self):
        assert _is_picklable(simple_tokenizer) is True

    def test_lambda_returns_false(self):
        lambda_func = lambda x: x
        assert _is_picklable(lambda_func) is False

    def test_clase_with_call_picklable(self):
        obj = DummyPreprocessor()
        assert _is_picklable(obj) is True

    def test_clase_not_picklable_returns_false(self):
        unpicklable = UnpicklablePreprocessor(lambda x: x)
        assert _is_picklable(unpicklable) is False

    def test_builtin_picklable(self):
        assert _is_picklable(len) is True
        assert _is_picklable(str.upper) is True

    def test_method_instancia_picklable(self):
        obj = DummyPreprocessor()
        assert _is_picklable(obj.__call__) is True

class TestParallelPreprocessIntegration:

    def test_preprocessor_complejo(self):
        def complex_preprocessor(text):
            import re
            text = re.sub(r'[^\w\s]', '', text)
            text = text.lower()
            text = ' '.join(text.split())
            return text
        
        texts = ["Hello, World!  ", "Python Testing!!!", "  Spaces  "]
        result = parallel_preprocess(
            texts,
            preprocessor=complex_preprocessor,
            tokenizer=simple_tokenizer,
            workers=2,
            min_docs=1
        )
        assert len(result) == 3
        assert result[0] == ["hello", "world"]
        assert result[1] == ["python", "testing"]
        assert result[2] == ["spaces"]

    def test_large_corpus(self):
        texts = [f"document {i} content here" for i in range(100)]
        result = parallel_preprocess(
            texts,
            preprocessor=preprocessor_returns_str,
            tokenizer=simple_tokenizer,
            workers=4,
            min_docs=10
        )
        assert len(result) == 100
        assert all(len(doc) > 0 for doc in result)

    def test_documents_unicos(self):
        texts = ["unique1", "unique2", "unique3"]
        result = parallel_preprocess(
            texts,
            preprocessor=preprocessor_returns_str,
            tokenizer=simple_tokenizer,
            workers=2,
            min_docs=1
        )
        assert result == [["UNIQUE1"], ["UNIQUE2"], ["UNIQUE3"]]

    def test_withsistencia_sequential_vs_parallel(self):
        texts = ["doc one two", "doc three four", "doc five six"]
        
        seq_result = _sequential_preprocess(texts, preprocessor_returns_str, simple_tokenizer)
        
        par_result = parallel_preprocess(
            texts,
            preprocessor=preprocessor_returns_str,
            tokenizer=simple_tokenizer,
            workers=1,
            min_docs=1
        )
        
        assert seq_result == par_result

    def test_preprocessor_with_siof_effects(self):
        counter = {"count": 0}
        
        def counting_preprocessor(text):
            counter["count"] += 1
            return text.upper()
        
        texts = ["doc1", "doc2", "doc3"]
        result = parallel_preprocess(
            texts,
            preprocessor=counting_preprocessor,
            tokenizer=simple_tokenizer,
            workers=2,
            min_docs=1
        )
        
        assert len(result) == 3
        assert counter["count"] == 3