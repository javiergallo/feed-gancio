from typing import List, Optional

from pydantic import FilePath
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict()

    classifier_model: str = "joeddav/xlm-roberta-large-xnli"
    llama_model_path: FilePath = "./llama-3.2-3b-instruct-q8_0.gguf"
    prompt_context_max_length: int = 1024
    temperature: float = 0.0
    image_selector: str = "img"

    locale: Optional[str] = None
    hypothesis_template: str = "This example is {}."
    assume_schedulable_event: bool = False
    schedulable_event_min_score: float = 0.4
    schedulable_event_label: str = "schedulable event"
    other_candidate_labels: List[str] = ["news", "statement"]
    date_format: str = "%A, %B %d, %Y"
    time_format: str = "%H hours and %M minutes"
    start_key: str = "start"
    end_key: str = "end"
    datetime_strs_extraction_prompt_template: str = (
        "You are a helpful assistant that extracts date-time "
        "information from text. You will be given a text that "
        "refers to a schedulable event. You must extract the "
        "event's start date-time, and ending date-time if "
        "possible (empty string if not possible). You must "
        "return the extracted information in a JSON object "
        "with the following keys: "
        "{start_key} and {end_key}. "
        "The values of the keys must be strings. The date-time "
        "strings must be in a format that can be parsed by "
        "dateparser.parse(). "
        "Today's {today_str}, it's {now_str}. "
    )
    datetime_extraction_prompt_template: str = (
        "You are a helpful assistant that extracts date-time information "
        "from text. You will be given a text that refers to date-time "
        "information. You must extract the date-time, ISO formatted. "
        "Today's {today_str}, it's {now_str}. "
    )
