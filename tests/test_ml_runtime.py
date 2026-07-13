from transformers.pipelines import PIPELINE_REGISTRY


def test_transformers_supports_summarization_pipeline():
    assert "summarization" in PIPELINE_REGISTRY.get_supported_tasks()
