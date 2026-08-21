from llama_cpp import Llama
from transformers import pipeline


def load_models(prompt_context_max_length: int) -> tuple:
    classifier = pipeline(
        "zero-shot-classification", model="joeddav/xlm-roberta-large-xnli"
    )
    llm = Llama(
        model_path="./llama-3.2-3b-instruct-q8_0.gguf",
        chat_format="chatml",
        n_ctx=prompt_context_max_length,
        verbose=False,
    )
    return classifier, llm
