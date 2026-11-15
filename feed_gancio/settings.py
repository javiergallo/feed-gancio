from typing import List, Optional

from pydantic import Field, FilePath
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict()

    classifier_model: str = Field(
        default="joeddav/xlm-roberta-large-xnli",
        description="Hugging Face model ID used to classify feed entries.",
    )
    llama_model_path: FilePath = Field(
        default="./llama-3.2-1b-instruct-q8_0.gguf",
        description="Path to the local GGUF language model file.",
    )
    prompt_context_max_length: int = Field(
        default=1024,
        description=(
            "Llama context-window size and maximum system-prompt length."
        ),
    )
    temperature: float = Field(
        default=0.0,
        description=(
            "Sampling temperature for the Llama model; used for datetime "
            "parsing."
        ),
    )
    image_selector: str = Field(
        default="img",
        description="CSS selector used to find an event image in feed HTML.",
    )

    locale: Optional[str] = Field(
        default=None,
        description="Optional locale for localized dates and times.",
    )
    hypothesis_template: str = Field(
        default="This example is {}.",
        description="Template used to score candidate labels for feed text.",
    )
    assume_schedulable_event: bool = Field(
        default=False,
        description=(
            "Skip classification and treat every feed entry as an event."
        ),
    )
    schedulable_event_min_score: float = Field(
        default=0.4,
        description="Minimum classifier score required to accept an event.",
    )
    schedulable_event_label: str = Field(
        default="schedulable event",
        description="Classifier label that identifies schedulable events.",
    )
    other_candidate_labels: List[str] = Field(
        default=["news", "statement"],
        description=(
            "Alternative labels compared with the schedulable-event label."
        )
    )
    date_format: str = Field(
        default="%A, %B %d, %Y",
        description="strftime format for the current date included in prompts.",
    )
    time_format: str = Field(
        default="%H hours and %M minutes",
        description="strftime format for the current time included in prompts.",
    )
    start_key: str = Field(
        default="start",
        description="JSON key used for the parsed event start datetime.",
    )
    end_key: str = Field(
        default="end",
        description="JSON key used for the parsed event end datetime.",
    )
    datetime_strs_extraction_prompt_template: str = Field(
        default=(
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
        ),
        description=(
            "Prompt template for extracting event start and end datetime "
            "strings."
        ),
    )
    datetime_extraction_prompt_template: str = Field(
        default=(
            "You are a helpful assistant that extracts date-time information "
            "from text. You will be given a text that refers to date-time "
            "information. You must extract the date-time, ISO formatted. "
            "Today's {today_str}, it's {now_str}. "
        ),
        description=(
            "Prompt template for normalizing one datetime to ISO format."
        ),
    )
