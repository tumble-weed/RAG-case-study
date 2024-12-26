import chunking
import retrieval
import json
import colorful
import argparse
from typing import Union
import warnings
warnings.simplefilter('ignore')
def main(
        synthetic : bool=False,
        k :int = 1,
        query :Union[str,None] = None,
        do_rerank: bool = True,
        ) -> None:
    """
    Demonstrates document retrieval based on provided or default queries.

    Processes a document (either synthetically generated using ChatGPT or the one provided 
    in the problem description) and splits it into chunks, which are then indexed in a vector 
    store for similarity search. The function reads queries from a file or accepts a single 
    query input. For each query, it retrieves relevant document chunks and displays their 
    content along with similarity scores.

    Args:
        synthetic: Determines whether to use a synthetic document (True) or a real document (False).
        k: Specifies the number of retrieval results to return for each query.
        query: A single query string to search or None to load a set of queries from a file.
        do_rerank: Whether to do reranking. True by default
    Returns:
        None. Prints the document and retrieval results for each query, showing matching 
        chunks with their associated context and similarity scores.
    """

    document_fname = 'data/document.json'
    if synthetic:
        document_fname = 'data/synthetic_document.json'
    with open(document_fname,'r') as f:
        document = json.load(f)
    chunks = chunking.process_document(document)
    vectorstore = retrieval.create_vector_store(chunks,overwrite=True)
    #=========================================================
    #queries = [
    #        "How do I configure IPv4?",
    #        "How do I do IPv4 configuration?",
    #        "what is the default value for Firewall?"
    #]
    if query is None:
        queries_fname = 'data/queries.json'
        if synthetic:
            queries_fname = 'data/queries_for_synthetic.json'
        with open(queries_fname,'r') as f:
            queries = json.load(f)
        queries = queries['queries']
    else:
        queries = [query]
    break_ = False
    print('='*60)
    print(colorful.blue('DOCUMENT'))
    print(colorful.pink(json.dumps(document,indent=4)))

    for iq,query in enumerate(queries):
        iq += 1
        # results = vectorstore.similarity_search(query, k=1)
        #results_and_scores = vectorstore.similarity_search_with_score(query, k=k)
        results_and_scores = retrieval.retrieve_and_rerank(query,vectorstore,k=k,first_k=4, do_rerank=do_rerank)
        #=======================================================
        print(colorful.blue(f'QUERY {iq}'))
        print(colorful.green(query))
        # Print matching chunks
        # for result,score in zip(results,scores):
        for i,(result,score) in enumerate(results_and_scores):
            i += 1
            print(colorful.blue(f'RETRIEVAL {i}'))
            print(colorful.cyan('Context'))
            print(colorful.yellow(json.dumps({k:v for k,v in result.metadata.items() if k not in ['raw_content']},indent=6)))
            print(colorful.cyan('Original Content'))
            print(colorful.yellow(json.dumps(result.metadata['raw_content'],indent=6)))
            print(colorful.cyan('Chunk'))
            print(colorful.yellow(result.page_content))
            #print(f'{colorful.blue("DISTANCE")}:{colorful.red(score)}')
            print(f'{colorful.blue("SCORE")}:{colorful.red(score)}')
            print('-'*60)
        print('='*60)
        while True:
            if iq == len(queries):
                break
            choice = input(f'Continue to next query {iq+1}/{len(queries)} [Enter]/ Quit (q)')
            choice = choice.lower()
            
            if len(choice) and choice[0] == 'q':
                break_ = True
                break
            if choice == '':
                break
        if break_: break

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--synthetic',action='store_true',default=False,help="use synthetic data for demo. default is to use the document provided in the problem statement")
    parser.add_argument('--k',default=1,type=int,help="number of documents to retrieve. Default 1")
    parser.add_argument('--query',default=None,type=str,help="your query. default is to pick up queries from data/queries*.json")
    parser.add_argument('--do_rerank',default=True,type=lambda t:t.lower()=='true',help="whether to do reranking. default is True, use --do_rerank false to disable")
    args = parser.parse_args()
    main(**vars(args))
