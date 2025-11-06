"""
data classification post-process: heuristics to choose one from best-of-n
lowest number of images. then have LLM choose which one is best. maybe there is metadata on image?
across the board, assume false positives unless all agree
check that monster stat blocks include same elements. only take the Union of all of them
"""
