# To Run

## Setup 

The requirements can be installed with 
```
pip install -r requirements.txt
```
You will need to set your OpenAI key in ```secrets.json``` .

## Running
The main entry point is ```demo.py``` . Running it without any arguments as ```python demo.py``` will run the following setting:

- The knowledge base/document used will be the one provided in the problem, stored in ```data/document.json```
- We will run ~20 queries to test retrieval. After each query the user is asked to choose to continue. 
- For each query the top 1 result will be retrieved.

For each query, the program prints out the **context** in the original document the chunk belongs to (the section, subsection etc.), the **original content** of the chunk, and the **chunk** stored in the vector store and utilized for retrieval.

Other possible runs include

**For a custom query**:

```python demo.py --query “How do I configure IPv4?” ```

**For a 2 retrievals per query**:

```python demo.py --k 2 ```

I also used ChatGPT to flesh out the document skeleton provided. This can be found in ```data/synthetic_document.json``` . The system can be tested with the synthetic document as:

```python demo.py --synthetic```

(Similar to the original skeleton document, it will run a panel of ~20 queries against this document.)

***To disable reranking***

```python demo.py --do_rerank false```

Some unittests are provided to view expected behaviors of 2 core functions ```process_document``` and ```retrieve_chunks```. These can be viewed in ```test.py``` and run as ```python -m unittest test.py```

---

# Overall Design

The information in the three keys ```content, code_block and table``` define chunks. Let’s call these ***chunkable blocks***. I deal with each of them in a different manner

## Normal Text (Content)

For ```content``` blocks, I prepend the ***Title*** to the beginning of the text. (Also see: **Document Hierarchy** below)

Example, for a document:

```
{
	"title": "System Configuration Guide",
	"sections": [
    	{
        	"title": "Network Settings",
        	"content": "Configure network parameters using the control panel...",
}
]
}
```

I get the chunk(s):

```
"Title: System Configuration Guide,Network Settings\n\nConfigure network parameters using the control panel..."
```

## Tables

For **tables** I flatten out the structure: I convert each row to a dictionary with the **headers as the keys** , and the values from the row. Finally we have a JSON-like structure as a  **list of dictionaries**, where each dictionary is a row. This is converted to a string and I prepend the **title** as a **python comment** to the top. 

Example, for a document:

```
{
	"title": "System Configuration Guide",
	"sections": [
{
        	"title": "Security",
        	"content": "Security settings must be configured according to...",
        	"table": {
            	"headers": [ "Setting", "Default","Recommended" ],
            	"rows": [
                	[ "Firewall", "Off", "On" ],
                	[ "Encryption", "AES-128", "AES-256" ]
            		]
        		}
    }
]
}
```

I get the chunk(s):

```
"# Table for: System Configuration Guide,Security\n[{\"Setting\": \"Firewall\", \"Default\": \"Off\", \"Recommended\": \"On\"}]"
"# Table for: System Configuration Guide,Security\n[{\"Setting\": \"Encryption\", \"Default\": \"AES-128\", \"Recommended\": \"AES-256\"}]"
```

## Code

I make the assumption that we are dealing with **Python** code. I prepend the **title** as a **pythonic comment (#)** as the first line.

Example, for a document:

```
{
	"title": "System Configuration Guide",
	"sections": [
    	{
        	"title": "Network Settings",
        	"subsections": [
            	{
                	"title": "IPv4 Configuration",
                	"code_block": "config.set_ip('192.168.1.1')"
            	}
        	]
}
]
}
```

I get the chunk(s):

```
"# Code Block for: System Configuration Guide,Network Settings,IPv4 Configuration\n\nconfig.set_ip('192.168.1.1')"
```

## Document Hierarchy

I accumulate the **titles** encountered in **traversing** to a chunkable block. For e.g. for a subsection, I will track the title of the book,title of  the parent section and title of this subsection. This list of titles is concatenated with a comma, and considered the “title” of the chunk. 

## Splitting chunks

For real world scenarios, we will encounter large chunkable blocks that will need to be split. These need to be addressed according to the data, but I demonstrate one idea here for tables.

For table chunks, I split while keeping rows intact. Each chunk created after splitting like this will be prepended with the title line as I outlined above. For example, for the document

```
    	document = {
        	'title': 'countries and captials',
        	'table': {
            	'headers' : ['country','capital'],
            	'rows': [
                	['india','new delhi'],
                	['japan','tokyo'],
                	['china','beijing'],
            	]
        	}
    	}
```

and the constraint that a chunk can hold only 1 row ( for demonstration purposes. In real world cases this limit would be much larger, and determined by tokens and not rows ) , we end up with chunks

```
[
'# Table for: countries and captials\n[{"country":"india","capital":"new delhi"}]',
'# Table for: countries and captials\n[{"country":"japan","capital":"tokyo"}]',
'# Table for: countries and captials\n[{"country":"china","capital":"beijing"}]',
]
```

Apart from the idea of adding the title as a comment, the splitting behavior can be observed.

---
# Design Choices

## Synthetic data

 Often at early stages when the specifications are more at an idea level, LLMs can help with creating synthetic data. As mentioned in the section on running the code, I fleshed out the skeleton document to a fuller one in ```data/synthetic_document.json```.

Similarly, some queries can be created for the document using LLMs. These can be found in ```data/queries.json``` and ```data/queries_for_synthetic.json``` 

Apart from human constructed queries, they are useful for testing the system

## Embeddings

We need embeddings that work both for code as well as natural text (I am chunking tables as a data structure similar to code as well ). After searching, I was not able to find evidence for a previous embedding I had found very useful, **instructOR**, as being trained on code. So I decided to rely on OpenAI’s **text-embedding-3-small** model, which documentation explicitly states are reliable for both code and natural language. (https://platform.openai.com/docs/guides/embeddings/ section **Code search using embeddings**). This is the smallest OpenAI model, and the cheapest.

## Reranking

I used a Cross Encoder for reranking. Cross encoders work on pairs of sentences and output a compatibility score. After initial retrieval, I pass the query along with each retrieved chunk through the cross-encoder to score it. The chunks are then sorted according to the scores. I ued the ***ms-marco-MiniLM-L-6-v2*** cross encoder model which was recommended in forums as a reasonable, lightweight choice.

Some queries Reranking has an effect on (for the provided skeleton document):

__What are the recommended security settings?__

***without reranking:***

Context

```
{
      "section": "Security"
}
```

Original Content

```"Security settings must be configured according to..."```

Chunk

```
Title: System Configuration Guide,Security

Security settings must be configured according to...
```

***with reranking***

Context

```
{
      "section": "Security"
}
```

Original Content

```"{'headers': ['Setting', 'Default', 'Recommended'], 'rows': [['Encryption', 'AES-128', 'AES-256']]}"```

Chunk

```
# Table for: System Configuration Guide,Security
[{"Setting": "Encryption", "Default": "AES-128", "Recommended": "AES-256"}]
```


__Is there a table summarizing security configurations?__

***without reranking***

Context

```
{
      "section": "Security"
}
```

Original Content

```"Security settings must be configured according to..."```

Chunk

```
Title: System Configuration Guide,Security

Security settings must be configured according to...
```

***with reranking***

Context

```
{
      "section": "Security"
}
```

Original Content

```"{'headers': ['Setting', 'Default', 'Recommended'], 'rows': [['Encryption', 'AES-128', 'AES-256']]}"```

Chunk

```
# Table for: System Configuration Guide,Security
[{"Setting": "Encryption", "Default": "AES-128", "Recommended": "AES-256"}]
```

## Vector Store & Similarity function

I relied on **ChromaDb** with standard **cosine similarity**. These are reasonable default choices, and I did not find reason to deliberate further on this.

---

# Future directions:

Some more ideas that might be worth trying for the scenario:

## Tables as tools

This would be an alternate to the chunking based retrieval used here. In this case, we encode the table as pandas dataframes. Further we define a tool to run a pandas query to the table, and allow the LLM to take the option to use the tool, where the llm also outputs the query as a python snippet to run. 

## Recursive splitting

For large text chunks, unlike the situation we have here in the toy example, we would involve recursive text splitting, a standard choice where the text is split by paragraphs, sentences etc etc till the token limit of the embedding model is reached. 

## Rejecting retrievals

Since the retrieval also provides a match score,  we could calibrate a threshold on a large number of queries to find a limit below which we’d reject the chunk, and not send it to the LLM. This could provide a way to catch irrelevant queries ( e.g. a user asking a customer support bot “who is harry potter’s mother?”). 


	

