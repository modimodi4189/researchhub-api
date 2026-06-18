from transformers import pipeline

summarizer = None


def get_summarizer():
    global summarizer
    if summarizer is None:
        # distilbart-cnn-12-6 is a dedicated summarization model (distilled BART
        # fine-tuned on CNN/DailyMail). FLAN-T5 is an instruction-tuned model —
        # using it with the "summarization" pipeline produces unreliable output.
        summarizer = pipeline(
            "summarization",
            model="sshleifer/distilbart-cnn-12-6",
            device=-1,  # CPU; set to 0 for GPU
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
