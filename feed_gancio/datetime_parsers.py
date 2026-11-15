import dateparser
import datetime
import json

from llama_cpp import Llama
from loguru import logger
from typing import Dict

from feed_gancio.settings import Config


class LlamaDatetimeParser:
    """Extract and parse event datetimes with the configured language model."""

    config: Config
    llm: Llama

    def __init__(self, config: Config, llm: Llama):
        self.config = config
        self.llm = llm

    def parse_datetime_strs(self, text: str) -> Dict[str, str]:
        """Extract event start and end datetime strings from text."""
        now = datetime.datetime.now()
        prompt = self.config.datetime_strs_extraction_prompt_template.format(
            start_key=self.config.start_key,
            end_key=self.config.end_key,
            today_str=now.strftime(self.config.date_format),
            now_str=now.strftime(self.config.time_format),
        )
        logger.debug(prompt)
        response = self.llm.create_chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": prompt[: self.config.prompt_context_max_length],
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
            response_format={
                "type": "json_object",
                "schema": {
                    "type": "object",
                    "properties": {
                        self.config.start_key: {"type": "string"},
                        self.config.end_key: {"type": "string"},
                    },
                },
            },
            temperature=self.config.temperature,
        )

        content = json.loads(response["choices"][0]["message"]["content"])

        assert isinstance(content, dict)
        assert self.config.start_key in content

        return content

    def parse_datetime(self, text: str) -> datetime.datetime:
        """Normalize a datetime expression to a Python datetime."""
        now = datetime.datetime.now()
        prompt = self.config.datetime_extraction_prompt_template.format(
            today_str=now.strftime(self.config.date_format),
            now_str=now.strftime(self.config.time_format),
        )
        response = self.llm.create_chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": prompt[: self.config.prompt_context_max_length],
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
            response_format={
                "type": "json_object",
                "schema": {
                    "type": "object",
                    "properties": {"iso_datetime": {"type": "string"}},
                },
            },
            temperature=self.config.temperature,
        )
        content = json.loads(response["choices"][0]["message"]["content"])

        assert isinstance(content, dict)
        assert "iso_datetime" in content

        return dateparser.parse(
            content["iso_datetime"], settings={"RETURN_AS_TIMEZONE_AWARE": False}
        )

    def parse_datetimes(self, text: str) -> Dict[str, datetime.datetime]:
        """Extract and parse event start and end datetimes from text."""
        datetimes = {}
        datetime_strs = self.parse_datetime_strs(text)
        datetimes[self.config.start_key] = self.parse_datetime(
            datetime_strs[self.config.start_key]
        )
        if self.config.end_key in datetime_strs:
            datetimes[self.config.end_key] = self.parse_datetime(
                datetime_strs[self.config.end_key]
            )
        return datetimes
