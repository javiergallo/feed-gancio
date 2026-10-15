import dateparser
import datetime
import feedparser
import io
import json
import mimetypes
import requests
import typer

from bs4 import BeautifulSoup
from llama_cpp import Llama
from loguru import logger
from transformers.pipelines.base import Pipeline
from typing import Dict, List, Optional

from feed_gancio.settings import Config


def flatten_hypertext(hypertext: str) -> str:
    """
    Parse HTML and extract clean text.
    """
    soup = BeautifulSoup(hypertext, "html.parser")
    return soup.get_text(separator=" ")


class FeedEventDownloader:
    """Download schedulable events from an RSS feed."""

    config: Config
    classifier: Pipeline
    llm: Llama

    def __init__(self, config: Config, classifier: Pipeline, llm: Llama):
        self.config = config
        self.classifier = classifier
        self.llm = llm

    def _is_schedulable_event(self, text: str) -> bool:
        """
        Determine whether some text refers to a schedulable event.
        """
        candidate_labels = [
            self.config.schedulable_event_label
        ] + self.config.other_candidate_labels
        hypothesis_template = self.config.hypothesis_template
        result = self.classifier(
            text, candidate_labels, hypothesis_template=hypothesis_template
        )
        labels = result.get("labels", [])
        scores = result.get("scores", [])
        logger.debug(list(zip(labels, scores)))
        return (
            labels[0] == self.config.schedulable_event_label
            and scores[0] >= self.config.schedulable_event_min_score
        )

    def _extract_datetime_strs(self, text: str) -> Dict[str, str]:
        """
        Extract datetimes from schedulable event text.
        """
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

    def _extract_datetime(self, text: str) -> datetime.datetime:
        """
        Extract datetime from text.
        """
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

    def _make_event(
        self,
        title: str,
        link: str,
        hypertext: str,
        start: datetime.datetime,
        end: Optional[datetime.datetime],
    ) -> dict:
        """Build a Gancio event payload from the supplied event details."""
        event_data = {
            "title": title,
            "description": hypertext,
            "start_datetime": int(start.timestamp()),
            "online_locations": [
                link,
            ],
        }
        if end:
            assert start <= end
            event_data["end_datetime"] = (int(end.timestamp()),)

        soup = BeautifulSoup(hypertext, "html.parser")
        image = soup.select_one(self.config.image_selector)
        if image:
            event_data.pop("online_locations", None)
            event_data.update(
                {
                    "image_url": image.get("src"),
                    "image_name": title,
                    "image_focalpoint": [[0, 0]],
                    "online_locations[]": link,
                }
            )
        return event_data

    def download_upcoming_schedulable_events(self, feed_url: str) -> List[dict]:
        """Download future schedulable events from an RSS feed."""
        events_data = []

        # Parse the RSS feed
        logger.info(f"Parsing feed from {feed_url}")
        feed = feedparser.parse(feed_url)

        # Print feed metadata
        logger.info(f"Feed metadata: {repr(feed.feed.title)} ({feed.feed.link})")

        # Loop through the feed entries
        for entry in feed.entries:
            try:
                entry_content = entry.content[0].value
            except AttributeError:
                entry_content = entry.description
            if entry_content:
                logger.info(f"Analyzing {repr(entry.title)}...")

                hypertext = entry_content
                text = flatten_hypertext(hypertext)

                if self.config.assume_schedulable_event or self._is_schedulable_event(
                    text
                ):
                    datetime_strs = self._extract_datetime_strs(text)
                    logger.debug(datetime_strs)

                    start = datetime_strs.get(self.config.start_key)
                    start = self._extract_datetime(start)

                    end = datetime_strs.get(self.config.end_key)
                    end = end and self._extract_datetime(end)

                    logger.debug(f"start: {repr(start)}, end: {repr(end)}")

                    now = datetime.datetime.now()

                    assert isinstance(start, datetime.datetime)
                    if start < now:
                        logger.info("Event has already began or it's finished.")
                    else:
                        event_data = self._make_event(
                            entry.title, entry.link, hypertext, start, end
                        )
                        events_data.append(event_data)
                        logger.info("Event downloaded.")
                        # break

                else:
                    logger.info("Text doesn't refer to a schedulable event.")
            else:
                logger.warning("There's no content")

        return events_data


class GancioEventSender:
    """Send events to Gancio."""

    gancio_url: str

    def __init__(self, gancio_url: str):
        self.gancio_url = gancio_url

    def send_event_to_gancio(self, event: dict):
        """Send one event to the Gancio endpoint."""
        logger.info(f"Scheduling {repr(event['title'])}...")

        try:
            image_url = event.pop("image_url")
        except KeyError:
            logger.info("Sending event without an image...")
            headers = {"Content-Type": "application/json"}
            response = requests.post(self.gancio_url, headers=headers, json=event)
        else:
            logger.info("Sending event with an image...")
            image_response = requests.get(image_url)
            image_mime_type = image_response.headers.get("Content-Type")
            image_extension = mimetypes.guess_extension(image_mime_type)
            image_data = (
                f"image{image_extension}",
                io.BytesIO(image_response.content),
                image_mime_type,
            )
            response = requests.post(
                self.gancio_url,
                data=event,
                files=[("image", image_data)],
            )

        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(response.json())

    def send_events_to_gancio(self, events: List[dict], interactive: bool = False):
        """Send events to Gancio, optionally confirming each submission."""
        for event in events:
            if interactive:
                typer.echo(json.dumps(event, indent=4, default=str))
                must_send = typer.confirm("Send this event to Gancio?")
            else:
                must_send = True

            if must_send:
                self.send_event_to_gancio(event)
