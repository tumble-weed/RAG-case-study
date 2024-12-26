#from langchain.embeddings import OpenAIEmbeddings
from langchain_community.embeddings import OpenAIEmbeddings
#from langchain.vectorstores import Chroma
from langchain_community.vectorstores import Chroma
from langchain.vectorstores.base import VectorStore
import os
import json
import shutil
from typing import Tuple, Union
from sentence_transformers import CrossEncoder
PERSIST_DIRECTORY = "./chroma_db"
# Set OpenAI API Key
with open('secrets.json','r') as f:
    os.environ["OPENAI_API_KEY"] = json.load(f)['OPENAI_API_KEY']
cross_encoder = CrossEncoder(
   "cross-encoder/ms-marco-TinyBERT-L-2-v2", max_length=512, device="cpu"
)
cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

def create_vector_store(chunks:list[dict], overwrite:bool=False) -> VectorStore:
    """Creates a vector store using OpenAI embeddings and ChromaDB.

    Args:
        chunks (list[dict]): A list of dictionaries where each dictionary contains 'text' and 'metadata' keys. 
            The 'text' is the content to be embedded, and 'metadata' contains relevant metadata for each chunk.
        overwrite (bool, optional): If True, existing vector store data at the persist directory will be 
            deleted before creating the new store. Defaults to False.

    Returns:
        VectorStore: A ChromaDB vector store containing the embedded text data, ready for querying and persistence.
    """
    # Initialize OpenAI Embeddings with text-embedding-3-small
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    # Create ChromaDB vector store
    if overwrite:
        if os.path.exists(PERSIST_DIRECTORY):
            shutil.rmtree(PERSIST_DIRECTORY)

    vectorstore = Chroma.from_texts(
        texts=[c['text'] for c in chunks],
        metadatas = [c['metadata'] for c in chunks],
        embedding=embeddings,
        persist_directory=PERSIST_DIRECTORY
    )
    return vectorstore

def retrieve_and_rerank(query: str,vectorstore : VectorStore , k: int, first_k: Union[None,int] = None, do_rerank : bool = True) -> list[Tuple[dict,float]]:
    """
    Retrieves the top-k most similar documents to a given query from a vector store and re-ranks them using a cross-encoder model.

    Args:
        query (str): The search query used to retrieve relevant documents.
        vectorstore (VectorStore): A vector store containing document embeddings for similarity search.
        k (int): The number of top similar documents to retrieve.
        first_k (None or int): The initial number of retrievals before reranking. If None, first_k = k. Default is None
    Returns:
        list[Tuple[dict, float]]: A sorted list of tuples where each tuple contains a document (dict) and its re-ranked similarity score (float).
    """
    if first_k is None or do_rerank is False:
        first_k = k
    results_and_scores = vectorstore.similarity_search_with_score(query, k=first_k)
    if do_rerank:
        #cross encoder reranker
        retrieved_texts = [r.page_content for r,s in results_and_scores]
        response = [[query, text] for text in retrieved_texts]
        cross_encoder_scores = cross_encoder.predict(response)
        results_and_scores = [(r,s1) for (r,s),s1 in zip(results_and_scores,cross_encoder_scores)]
        results_and_scores = list(sorted(results_and_scores,key=lambda el:el[1],reverse=True))[:k]
    return results_and_scores
def retrieve_chunks(query: str, chunks: list[dict], top_k: int = 3) -> list[dict]:
    """
    Retrieve the most relevant chunks for a given query from a list of chunk dictionaries.

    Args:
        query (str): The search query to find relevant chunks.
        chunks (list[dict]): A list of dictionaries containing chunk data, including 'page_content' and metadata.
        top_k (int, optional): The number of top relevant chunks to return. Default is 3.

    Returns:
        list[dict]: A list of dictionaries, each containing:
            - 'score': The relevance score of the chunk.
            - 'chunk': The chunk content related to the query.
            - 'original_content': The raw content of the chunk.
            - 'context': Metadata of the chunk, excluding 'raw_content'.
    """
    vectorstore = create_vector_store(chunks,overwrite=True)
    #results_and_scores = vectorstore.similarity_search_with_score(query, k=top_k)
    results_and_scores = retrieve_and_rerank(query,vectorstore,top_k)
    results = [{'score':2-dist,'chunk':r.page_content, 'original_content': r.metadata['raw_content'], 'context':{k:v for k,v in r.metadata.items() if k not in ['raw_content']}} for r,dist in results_and_scores]
    return results

