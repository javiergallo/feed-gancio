import dateparser
import datetime
import feedparser
import json
import logging
import os
import requests
import typer
import urllib.request

from bs4 import BeautifulSoup
from loguru import logger
from typing import Dict, List, Optional

from feed_gancio.settings import Config


def flatten_hypertext(hypertext: str) -> str:
    """
    Parse HTML and extract clean text.
    """
    soup = BeautifulSoup(hypertext, "html.parser")
    return soup.get_text(separator=" ")


def is_schedulable_event(config: Config, classifier, text: str) -> bool:
    """
    Determine whether some text refers to a schedulable event.
    """
    candidate_labels = [config.schedulable_event_label] + config.other_candidate_labels
    hypothesis_template = config.hypothesis_template
    result = classifier(
        text, candidate_labels, hypothesis_template=hypothesis_template
    )
    labels = result.get("labels", [])
    scores = result.get("scores", [])
    logger.debug(list(zip(labels, scores)))
    return (
        labels[0] == config.schedulable_event_label and
        scores[0] >= config.schedulable_event_min_score
    )


def extract_datetime_strs(config: Config, llm, text: str) -> Dict[str, str]:
    """
    Extract datetimes from schedulable event text.
    """
    now = datetime.datetime.now()
    prompt = config.datetime_strs_extraction_prompt_template.format(
        today_str=now.strftime(config.date_format),
        now_str=now.strftime(config.time_format),
        text=text,
    )
    logger.debug(prompt)
    response = llm.create_chat_completion(
        messages=[
            {"role": "user", "content": prompt[:config.prompt_context_max_length]}
        ],
        response_format={
            "type": "json_object",
            "schema": {
                "type": "object",
                "properties": {
                    config.start_key: {"type": "string"},
                    config.end_key: {"type": "string"}
                },
            },
        },
        temperature=config.temperature,
    )

    content = json.loads(response["choices"][0]["message"]["content"])

    assert isinstance(content, dict)
    assert config.start_key in content

    return content


def extract_datetime(config: Config, llm, text: str) -> datetime.datetime:
    """
    Extract datetime from text.
    """
    now = datetime.datetime.now()
    prompt = config.datetime_extraction_prompt_template.format(
        today_str=now.strftime(config.date_format),
        now_str=now.strftime(config.time_format),
        text=text,
    )
    response = llm.create_chat_completion(
        messages=[
            {"role": "user", "content": prompt[:config.prompt_context_max_length]}
        ],
        response_format={
            "type": "json_object",
            "schema": {
                "type": "object",
                "properties": {"iso_datetime": {"type": "string"}},
            },
        },
        temperature=config.temperature,
    )
    content = json.loads(response["choices"][0]["message"]["content"])

    assert isinstance(content, dict)
    assert "iso_datetime" in content

    return dateparser.parse(
        content["iso_datetime"], settings={"RETURN_AS_TIMEZONE_AWARE": False}
    )


def download_upcoming_schedulable_events(
    config: Config, classifier, llm, feed_url: str, # cache_file_path: str = FILE_PATH
) -> List[dict]:
    events_data = []
    
    # Parse the RSS feed
    feed = feedparser.parse(feed_url)

    # if not os.path.isfile(cache_file_path):
    #     # Download the remote RSS feed content and save it to a file
    #     logger.info("Downloading feed from %s...", feed_url)
    #     urllib.request.urlretrieve(feed_url, cache_file_path)

    # # Parse the locally stored file using feedparser
    # logger.info(f"Parsing feed from local file: {cache_file_path}")
    # feed = feedparser.parse(cache_file_path)

    # Print feed metadata
    logger.info(f"Feed metadata: {repr(feed.feed.title)} ({feed.feed.link})")

    # Loop through the feed entries (limiting to the top 5)
    for entry in feed.entries:
        try:
            entry_content = entry.content[0].value
        except AttributeError:
            entry_content = entry.description
        if entry_content:
            logger.info(f"Analyzing {repr(entry.title)}...")

            hypertext = entry_content
            text = flatten_hypertext(hypertext)

            if is_schedulable_event(config, classifier, text):
                datetime_strs = extract_datetime_strs(config, llm, text)
                logger.debug(datetime_strs)

                start = datetime_strs.get(config.start_key)
                start = extract_datetime(config, llm, start)

                end = datetime_strs.get(config.end_key)
                end = end and extract_datetime(config, llm, end)

                logger.debug(f"start: {repr(start)}, end: {repr(end)}")

                now = datetime.datetime.now()

                assert isinstance(start, datetime.datetime)
                if start < now:
                    logger.info("Event has already began or it's finished.")
                else:
                    event_data = {
                        "title": entry.title,
                        "description": hypertext,
                        "start_datetime": int(start.timestamp()),
                        "online_locations": [entry.link],  # FIXME
                    }
                    if end:
                        assert start <= end
                        event_data["end_datetime"] = int(end.timestamp()),
                    
                    soup = BeautifulSoup(hypertext, "html.parser")
                    image = soup.select_one(config.image_selector)
                    #if image:
                    #    event_data["image_url"] = image.get("src")

                    events_data.append(event_data)
                    logger.info("Event downloaded.")

            else:
                logger.info("Text doesn't refer to a schedulable event.")
        else:
            logger.warning("There's no content")

    return events_data


def send_event_to_gancio(event: dict, gancio_url: str):
    logger.info(f"Scheduling {repr(event['title'])}...")

    headers = {"Content-Type": "application/json"}

    response = requests.post(gancio_url, headers=headers, json=event)

    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(response.json())


def send_events_to_gancio(
    events: List[dict], gancio_url: str, interactive: bool = False
):
    for event in events:
        if interactive:
            typer.echo(json.dumps(event, indent=4, default=str))
            must_send = typer.confirm("Send this event to Gancio?")
        else:
            must_send = True

        if must_send:
            send_event_to_gancio(event, gancio_url)
