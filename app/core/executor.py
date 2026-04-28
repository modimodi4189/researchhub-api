from concurrent.futures import ThreadPoolExecutor

# Limits concurrent ML model calls (summarization, classification) to avoid OOM.
ml_executor = ThreadPoolExecutor(max_workers=2)
