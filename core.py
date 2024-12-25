import json
import copy

# TODO: recursive splitting on simple text and tables
# dprint = print
dprint = lambda *args,**kwargs:None
def flatten_chunks(document: dict,
                   metadata : dict = {},
                   titles: list = [],
                   level:int = 0) -> list[dict]:
    '''
    Presence of these keys means that we have information "worth" it's own chunk
    '''
    CHUNK_ANCHOR_KEYS = ["content","code_block","table"]

    # if level == 0:
    #     import pdb;pdb.set_trace()
    dprint('-'*50)
    dprint(document,titles)
    chunks = []
    '''
    # to give context to the info, we will accumulate all the "titles" seen till we get to it.
    # for e.g. for a subsection, we'd see probably 3 titles from the root level
    '''
    if 'title' in document:
        titles.append(document['title'])
    for k in CHUNK_ANCHOR_KEYS:
        if k in document:
            # import pdb;pdb.set_trace()
            chunks.append({})
            chunks[-1][k] = document[k]
            chunks[-1]['titles'] = titles
            chunks[-1]['metadata'] = metadata
    # print(document.keys())
    '''
    Check if at this level is there a key ending with sections, e.g. sections, subsections, subsubsections etc.
    If so recursively call process_document
    '''
    for k in document:
        if k.endswith('sections'):
            for inner_document in document[k]:
                if 'title' in inner_document:
                    metadata[k[:-1]] = inner_document['title']
                dprint(f'found {k}, calling flatten_chunks again')
                dprint(inner_document)
                inner_chunks = flatten_chunks(inner_document,
                                    # titles=[t for t in titles],
                                    titles=copy.copy(titles),
                                    metadata = copy.copy(metadata),
                                    level=level+1)
                chunks.extend(inner_chunks)
    dprint(chunks)
    return chunks

def standardize_chunks(
                        chunks:list[dict],
                        N_MAX_TABLE_ROWS: int = 1,
                       ) -> list[dict]:
    '''
    # POST PROCESSORS
    For embedding we'll collapse all types of chunks to pure text. For e.g.
    we'll add the titles as text to the content
    we'll add the titles as a comment to the code
    '''
    to_remove = []
    new_chunks = []
    for ic,chunk in enumerate(chunks):
        '''
        # content
        '''
        if 'content' in chunk and 'titles' in chunk:
            # assert False
            titles = chunk['titles']
            new_title = f"Title: {','.join(titles)}"

            new_content = new_title + '\n\n' + chunk['content']
            # new_chunk = {'content':new_content}
            new_chunk = new_content
            # chunks[ic] = new_chunk
            # chunks[ic] = dict(text=new_chunk,metadata=chunk['metadata'])
            new_chunks.append(dict(text=new_chunk,metadata=chunk['metadata']))
        '''
        # code. NOTE/ASSUMPTION: we have python code
        '''
        if 'code_block' in chunk and 'titles' in chunk:
            titles = chunk['titles']
            new_title = f"# Code Block for: {','.join(titles)}"
            new_code_block = new_title + '\n\n' + chunk['code_block']
            # new_chunk = {'code_block':new_code_block}
            new_chunk = new_code_block
            # chunks[ic] = new_chunk
            # chunks[ic] = dict(text=new_chunk,metadata=chunk['metadata'])
            new_chunks.append( dict(text=new_chunk,metadata=chunk['metadata']))
        '''
        # table
        '''
        #========================================================
        # flatten table
        if 'table' in chunk and 'titles' in chunk:
            # to_remove.append(ic)
            titles = chunk['titles']
            new_title = f"# Table for: {','.join(titles)}"
            headers = chunk['table']['headers']
            rows = chunk['table']['rows']

            new_table = []
            for row in rows:
                new_row = {}
                for h,el in zip(headers,row):
                    new_row[h] = el
                new_table.append(new_row)
            #-------------------------------------------------------------------
            # split the rows by  N_MAX_TABLE_ROWS
            n_chunks = (len(rows) + N_MAX_TABLE_ROWS - 1)//N_MAX_TABLE_ROWS
            for j in range(n_chunks):

                table_chunk = new_table[j*N_MAX_TABLE_ROWS:(j+1)*N_MAX_TABLE_ROWS]
                table_as_text = json.dumps(table_chunk)
                table_as_text = f'{new_title}\n{table_as_text}'
                new_chunks.append(dict(text=table_as_text,metadata=chunk['metadata']))
    new_chunks = [ c for ic,c in enumerate(new_chunks) if ic not in to_remove ]
    return new_chunks
def process_document(document: dict) -> list[dict]:
    chunks = flatten_chunks(document,titles=[])
    chunks = standardize_chunks(chunks)
    return chunks

