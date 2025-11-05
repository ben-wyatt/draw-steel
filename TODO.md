# To-do

## general

- file cleanup
- fastAPI backend: needs architecting
- rewrite ugly-chat for less code-nesting (quality)


## data formatting 
### structured data

- data classification post-process: heuristics to choose one from best-of-n
- image retrieval

### unstructured data

- better chunking for qdrant database: build chunk investigator
- investigate qdrant sparse vectors
- late-interaction models: retrieve with higher top_k, then do token-level embedding to rerank a la colBERT. does it make sense given our total number of chunks is low?


## frontend

- first round at front end -- does it require proper qdrant server?
 - to start should have only one page: chatbot with custom retrieval UI elements showing what data was retrieved.  should have easy click into PDF with side window
- integrate abilities, classes, monster blocks as UI elements
- second page: agentic search. LLM handles multiple calls to answer complex questions.
