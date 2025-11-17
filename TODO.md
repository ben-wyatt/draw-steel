# To-do


## general

- file cleanup
 - mechanics
 - models
 - rules
 - structured_filtering
- fastAPI backend: needs architecting
- rewrite ugly-chat for less code-nesting (quality)
- what to do with rules files: are they useful still?

## uglier_chat

- comb through interface
- expand context to previous and future chunks
- update tool settings on the fly based on commands
- print costs
- chunk "caching": if it's been retrieved in this chat history then don't print it again
- actually create chat history. with context caching?



## data formatting 
### structured data


- data classification post-process: heuristics to choose one from best-of-n
lowest number of images. then have LLM choose which one is best. maybe there is metadata on image?
across the board, assume false positives unless all agree
check that monster stat blocks include same elements. only take the Union of all of them

### images

best way to handle this is first extract all art via pymupdf
then summarize image (with surrounding 3 pages of content)
save with page number
upon retrieval: llm/deterministic decision to show image

### unstructured data

- better chunking for qdrant database: build chunk investigator DONE
- investigate qdrant sparse vectors
- late-interaction models: retrieve with higher top_k, then do token-level embedding to rerank a la colBERT. does it make sense given our total number of chunks is low?


## frontend

- first round at front end -- does it require proper qdrant server?
 - to start should have only one page: chatbot with custom retrieval UI elements showing what data was retrieved.  should have easy click into PDF with side window
- integrate abilities, classes, monster blocks as UI elements
- second page: agentic search. LLM handles multiple calls to answer complex questions.
