# To-do

- better chunking for qdrant database: build chunk investigator
- fastAPI backend: needs architecting
- first round at front end -- does it require proper qdrant server?
 - to start should have only one page: chatbot with custom retrieval UI elements showing what data was retrieved.  should have easy click into PDF with side window
- investigate qdrant sparse vectors
- late-interaction models: retrieve with higher top_k, then do token-level embedding to rerank a la colBERT
- integrate abilities, classes, monster blocks, as data structures, then UI elements
- image retrieval
- second page: agentic search. LLM handles multiple calls to answer complex questions.
