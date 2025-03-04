import os.path
from pathlib import Path

try:
    from tableserializer.serializer import Serializer
    from target_benchmark.evaluators import TARGET
    from hashlib import sha1
    import numpy as np
    from openai import OpenAI
    from typing import Dict, Optional, List

    from pytei import TEIClient
    from pytei.store import DuckDBEmbeddingStore
    from target_benchmark.retrievers import AbsStandardEmbeddingRetriever
except ImportError:
    raise Exception("Cannot use TARGET integration. Please install table serialization kitchen with the TARGET integration through 'pip install tableserializer[target]'")


class CachingOpenAIClient:

    def __init__(self, api_key: str, cache_db_path: str, model_name: str = "text-embedding-3-small"):
        self._client = OpenAI(api_key=api_key)
        db_parent_dir = Path(cache_db_path).parent
        if not os.path.exists(db_parent_dir):
            os.makedirs(db_parent_dir)
        self._store = DuckDBEmbeddingStore(cache_db_path)
        self.model_name = model_name

    def embed(self, text: str) -> np.ndarray:
        text_hash = sha1(text.encode()).hexdigest()
        try:
            return self._store.get(text_hash)
        except KeyError:
            response = self._client.embeddings.create(
                input=text,
                model=self.model_name
            )
            embedding = response.data[0].embedding
            embedding = np.array(embedding, dtype=np.float32)
            self._store.put(text_hash, embedding)
            return embedding

    def batch_embed(self, texts: List[str]) -> List[np.ndarray]:
        embedding_results = np.zeros(shape=(len(texts),), dtype=np.ndarray)
        call_indices = []
        call_texts = []
        text_hashes = [sha1(input_str.encode()).hexdigest() for input_str in texts]
        for index, input_str in enumerate(texts):
            try:
                embedding_results[index] = self._store.get(text_hashes[index])
            except KeyError:
                call_indices.append(index)
                call_texts.append(input_str)
        if len(call_indices) > 0:
            # Only call the embedding endpoint for inputs with cache misses
            embeddings = self._client.embeddings.create(input=call_texts, model=self.model_name)
            embeddings = [np.array(emb.embedding, dtype=np.float32) for emb in embeddings.data]
            for index, embedding in enumerate(embeddings):
                self._store.put(text_hashes[call_indices[index]], embedding)
            embedding_results[call_indices] = embeddings
        return embedding_results.tolist()


class ConfigurableRetriever(AbsStandardEmbeddingRetriever):

    def __init__(self, serializer: Serializer, tei_endpoint: str = "http://127.0.0.1:8001",
                 db_path: str = "cache/embedding_cache.duckdb", query_embedding_db_path: Optional[str] = None, embedding_batch_size: Optional[int] = None):
        super().__init__(expected_corpus_format="dataframe", embedding_batch_size=embedding_batch_size)
        self.serializer = serializer
        db_parent_dir = Path(db_path).parent
        if not os.path.exists(db_parent_dir):
            os.makedirs(db_parent_dir)
        self.corpus_tei_client = TEIClient(url=tei_endpoint, embedding_store=DuckDBEmbeddingStore(db_path=db_path))
        self.query_tei_client = self.corpus_tei_client
        if query_embedding_db_path is not None:
            self.query_tei_client = TEIClient(url=tei_endpoint,
                                              embedding_store=DuckDBEmbeddingStore(db_path=query_embedding_db_path))

    def embed_query(self, query: str, dataset_name: str, **kwargs) -> np.ndarray:
        return self.query_tei_client.embed(query)

    def batch_embed_queries(self, queries: List[str], dataset_name: str) -> List[np.ndarray]:
        return self.query_tei_client.embed(queries)

    def embed_corpus(self, dataset_name: str, corpus_entry: Dict) -> np.ndarray:
        serialized_table = self.serializer.serialize(corpus_entry["table"], metadata=corpus_entry["context"])
        return self.corpus_tei_client.embed(serialized_table)

    def batch_embed_corpora(self, dataset_name: str, corpus_entries: List[Dict]) -> List[np.ndarray]:
        serialized_corpora = [self.serializer.serialize(corpus_entry["table"], metadata=corpus_entry["context"]) for corpus_entry in corpus_entries]
        return self.corpus_tei_client.embed(serialized_corpora)


class ConfigurableOpenAIRetriever(AbsStandardEmbeddingRetriever):

    def __init__(self, serializer: Serializer, api_key: str, db_path: str = "cache/embedding_cache.duckdb",
                 query_embedding_db_path: Optional[str] = None, embedding_model_name: str = "text-embedding-3-small",
                 embedding_batch_size: Optional[int] = None):
        super().__init__(expected_corpus_format="dictionary", embedding_batch_size=embedding_batch_size)
        self.serializer = serializer
        self.corpus_openai_client = CachingOpenAIClient(api_key=api_key, cache_db_path=db_path, model_name=embedding_model_name)
        self.query_openai_client = self.corpus_openai_client
        if query_embedding_db_path is not None:
            self.query_openai_client = CachingOpenAIClient(api_key=api_key, cache_db_path=query_embedding_db_path, model_name=embedding_model_name)


    def embed_query(self, query: str, dataset_name: str) -> np.ndarray:
        return self.query_openai_client.embed(query)

    def batch_embed_queries(self, queries: List[str], dataset_name: str) -> List[np.ndarray]:
        return self.query_openai_client.batch_embed(queries)

    def embed_corpus(self, dataset_name: str, corpus_entry: Dict) -> np.ndarray:
        serialized_table = self.serializer.serialize(corpus_entry["table"], metadata=corpus_entry["context"])
        return self.corpus_openai_client.embed(serialized_table)

    def batch_embed_corpora(self, dataset_name: str, corpus_entries: List[Dict]) -> List[np.ndarray]:
        serialized_corpora = [self.serializer.serialize(corpus_entry["table"], metadata=corpus_entry["context"]) for corpus_entry in corpus_entries]
        return self.corpus_openai_client.batch_embed(serialized_corpora)


class TARGETOpenAIExperimentExecutor:

    def __init__(self, api_key: str, dataset_name: str, split: str = "test",
                 embedding_model_name: str = "text-embedding-3-small", top_k: int = 20,
                 embedding_cache_dir: str = None) -> None:
        self.embedding_model_name = embedding_model_name
        self.api_key = api_key
        self.dataset_name = dataset_name
        self.split = split
        self.top_k = top_k
        if embedding_cache_dir is None:
            embedding_cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "embedding_cache")
        self.table_cache_db_path = os.path.join(embedding_cache_dir, f"embedding_cache_{dataset_name}_{embedding_model_name}.duckdb")
        self.query_cache_db_path = os.path.join(embedding_cache_dir, f"query_embedding_cache_{dataset_name}_{embedding_model_name}.duckdb")

    def run_experiment(self, experiment_folder: str, serializer: Serializer) -> None:
        retriever = ConfigurableOpenAIRetriever(serializer=serializer, api_key=self.api_key,
                                                db_path=self.table_cache_db_path,
                                                query_embedding_db_path=self.query_cache_db_path,
                                                embedding_model_name=self.embedding_model_name, embedding_batch_size=64)
        target = TARGET(("Table Retrieval Task", self.dataset_name))
        experiment_results_folder = os.path.join(experiment_folder,
                                                 f"results_{self.dataset_name}_{self.sanatized_embedding_model_name}")
        results = target.run(retriever=retriever, split=self.split, top_k=self.top_k, batch_size=32,
                             retrieval_results_dir=experiment_results_folder)

class TARGETTEIExperimentExecutor:

    def __init__(self, embedding_model_name: str, dataset_name: str, split: str = "test",
                 tei_endpoint: str = "http://127.0.0.1:8001", top_k: int = 20, embedding_cache_dir: str = None,
                 batch_size: int = 32) -> None:
        self.embedding_model_name = embedding_model_name
        self.sanatized_embedding_model_name = embedding_model_name.lower().replace(' ', '_').replace('.', '_').replace('-', '_')
        self.dataset_name = dataset_name
        self.split = split
        self.tei_endpoint = tei_endpoint
        self.top_k = top_k
        self.batch_size = batch_size
        if embedding_cache_dir is None:
            embedding_cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "embedding_cache")
        self.table_cache_db_path = os.path.join(embedding_cache_dir, f"embedding_cache_{dataset_name}_{self.sanatized_embedding_model_name}.duckdb")
        self.query_cache_db_path = os.path.join(embedding_cache_dir, f"query_embedding_cache_{dataset_name}_{self.sanatized_embedding_model_name}.duckdb")

    def run_experiment(self, experiment_folder: str, serializer: Serializer) -> None:
        retriever = ConfigurableRetriever(serializer=serializer, tei_endpoint=self.tei_endpoint,
                                          db_path=self.table_cache_db_path,
                                          query_embedding_db_path=self.query_cache_db_path,
                                          embedding_batch_size=self.batch_size)
        target = TARGET(("Table Retrieval Task", self.dataset_name))
        experiment_results_folder = os.path.join(experiment_folder,
                                                 f"results_{self.dataset_name}_{self.sanatized_embedding_model_name}")
        results = target.run(retriever=retriever, split=self.split, top_k=self.top_k, batch_size=32,
                             retrieval_results_dir=experiment_results_folder)
