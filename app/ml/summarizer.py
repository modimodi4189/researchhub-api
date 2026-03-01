from transformers import pipeline

summarizer = None


def get_summarizer():
    global summarizer
    if summarizer is None:
        summarizer = pipeline(
            "summarization",
            model="google/flan-t5-base",
            device=-1  # CPU (-1), use 0 for GPU
        )
    return summarizer


def summarize_text(text: str, max_length: int = 150, min_length: int = 40) -> str:
    if not text or len(text.strip()) < 50:
        return text or ""
    
    summarizer = get_summarizer()
    
    # Truncate if too long (model has token limits)
    text = text[:2000]
    
    try:
        result = summarizer(
            text,
            max_length=max_length,
            min_length=min_length,
            do_sample=False
        )
        return result[0]['summary_text']
    except Exception as e:
        return f"Error generating summary: {str(e)}"


def summarize_long_text(text: str, max_length: int = 150) -> str:
    """Split long text into chunks and summarize each."""
    if not text or len(text.strip()) < 50:
        return text or ""
    
    # Split into chunks of ~1000 chars
    chunks = []
    words = text.split()
    current_chunk = []
    current_length = 0
    
    for word in words:
        current_length += len(word) + 1
        if current_length > 800:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            current_length = 0
        current_chunk.append(word)
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    # Summarize each chunk
    summarizer = get_summarizer()
    summaries = []
    
    for chunk in chunks:
        try:
            result = summarizer(
                chunk,
                max_length=max_length,
                min_length=30,
                do_sample=False
            )
            summaries.append(result[0]['summary_text'])
        except:
            continue
    
    if summaries:
        return ' '.join(summaries)
    
    return text[:500]
