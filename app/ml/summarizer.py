from transformers import pipeline

summarizer = None


def get_summarizer():
    global summarizer
    if summarizer is None:
        # distilbart-cnn-12-6 is a dedicated summarization model (distilled BART).
        # FLAN-T5 is an instruction-tuned model — using it with the "summarization"
        # pipeline produces unreliable output. Use text2text-generation + a prompt
        # if you want FLAN-T5; for plug-and-play summarization use BART.
        summarizer = pipeline(
            "summarization",
            model="sshleifer/distilbart-cnn-12-6",
            device=-1,  # CPU; use 0 for GPU
        )
    return summarizer


def summarize_text(text: str, max_length: int = 150, min_length: int = 40) -> str:
    if not text or len(text.strip()) < 50:
        return text or ""

    pipe = get_summarizer()
    text = text[:2000]  # model token limit

    try:
        result = pipe(text, max_length=max_length, min_length=min_length, do_sample=False)
        return result[0]["summary_text"]
    except Exception as e:
        return f"Error generating summary: {e}"


def summarize_long_text(text: str, max_length: int = 150) -> str:
    """Split long text into chunks and summarise each, then join."""
    if not text or len(text.strip()) < 50:
        return text or ""

    words = text.split()
    chunks, current_chunk, current_length = [], [], 0

    for word in words:
        current_length += len(word) + 1
        if current_length > 800:
            chunks.append(" ".join(current_chunk))
            current_chunk, current_length = [], 0
        current_chunk.append(word)

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    pipe = get_summarizer()
    summaries = []

    for chunk in chunks:
        try:
            result = pipe(chunk, max_length=max_length, min_length=30, do_sample=False)
            summaries.append(result[0]["summary_text"])
        except Exception:
            continue

    return " ".join(summaries) if summaries else text[:500]
