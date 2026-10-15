from typing import Tuple

from llama_cpp import Llama
from transformers import pipeline
from transformers.pipelines.base import Pipeline

from feed_gancio.settings import Config


def load_models(config: Config) -> Tuple[Pipeline, Llama]:
    classifier = pipeline("zero-shot-classification", model=config.classifier_model)
    llm = Llama(
        model_path=str(config.llama_model_path),
        chat_format="chatml",
        n_ctx=config.prompt_context_max_length,
        verbose=False,
    )
    return classifier, llm
