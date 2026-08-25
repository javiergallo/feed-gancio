from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict()

    prompt_context_max_length: int = 1024
    temperature: float = 0.0
    image_selector: str = "img"

    locale: Optional[str] = None
    hypothesis_template: str = "This example is {}."
    assume_schedulable_event: bool = False
    schedulable_event_min_score: float = 0.4
    schedulable_event_label: str ="schedulable event"
    other_candidate_labels: List[str] = ["news", "statement"]
    date_format: str = "%A, %B %d, %Y"
    time_format: str = "%H hours and %M minutes"
    start_key: str = "start"
    end_key: str = "end"
    datetime_strs_extraction_prompt_template: str = (
        "Today's {today_str}, it's {now_str}. "
        "The text below refers to a schedulable event. "
        "Extract the event's start date-time, and ending date-time if possible "
        "(empty string if not possible), from the text below:\n\n{text}"
    )
    datetime_extraction_prompt_template: str = (
        "Today's {today_str}, it's {now_str}. "
        "Extract date-time from the following text, ISO formatted: {text}"
    )
