import datetime
import json
import locale
import os
import pytest

from pathlib import Path
from types import SimpleNamespace

from hypothesis import given, settings, strategies as st
import pytest

import feed_gancio.utils as utils
from feed_gancio.models import load_models
from feed_gancio.settings import Config


def make_test_config(**kwargs) -> Config:
    return Config(_env_file=None, llama_model_path=Path(__file__), **kwargs)


@pytest.mark.parametrize("n_upcoming_events", [0, 1, 2])
@pytest.mark.integration
def test_download_upcoming_events(n_upcoming_events: int):
    """
    Given:
        * A local RSS fixture and loaded classifier and language models.
    When:
        * Upcoming schedulable events are downloaded from the fixture.
    Then:
        * The result contains the expected number of events.
        * Every event is represented by a dictionary.
    """
    config = Config(_env_file="es.env")

    if config.locale is not None:
        locale.setlocale(locale.LC_TIME, config.locale)

    classifier, llm = load_models(config)

    cur_dir_path = os.path.dirname(os.path.abspath(__file__))
    feed_downloader = utils.FeedEventDownloader(config, classifier, llm)
    events_data = feed_downloader.download_upcoming_schedulable_events(
        feed_url=f"{cur_dir_path}/test-feed-{n_upcoming_events}.xml",
    )

    assert isinstance(events_data, list)
    assert len(events_data) == n_upcoming_events
    for event_data in events_data:
        assert isinstance(event_data, dict)


@given(hypertext=st.text(max_size=256))
def test_flatten_hypertext_handles_generated_text(hypertext: str):
    """
    Given:
        * Arbitrary text of up to 256 characters.
    When:
        * The text is parsed as hypertext and flattened.
    Then:
        * The result is a string.
    """
    assert isinstance(flatten_hypertext(hypertext), str)


@settings(max_examples=40)
@given(
    is_schedulable=st.booleans(),
    score=st.floats(
        min_value=0, max_value=1, allow_nan=False, allow_infinity=False
    ),
    text=st.text(max_size=100),
)
def test_schedulable_classifier_decision(
    is_schedulable: bool, score: float, text: str
):
    """
    Given:
        * A generated text, classifier label, and score between 0 and 1.
    When:
        * The downloader checks whether the text describes a schedulable event.
    Then:
        * It returns true only for the target label with a score at or above the
        threshold.
    """
    config = make_test_config()

    def classifier(*args, **kwargs):
        label = config.schedulable_event_label if is_schedulable else "news"
        return {"labels": [label], "scores": [score]}

    downloader = utils.FeedEventDownloader(config, classifier, llm=None)

    assert downloader._is_schedulable_event(text) is (
        is_schedulable and score >= config.schedulable_event_min_score
    )


@settings(max_examples=20)
@given(
    entries=st.lists(
        st.tuples(
            st.text(max_size=30),
            st.from_regex(r"https://example\.com/[a-z]{1,12}", fullmatch=True),
            st.text(min_size=1, max_size=100),
        ),
        max_size=4,
    ),
    days_in_future=st.integers(min_value=1, max_value=365),
)
def test_download_upcoming_events_with_generated_feed(
    entries, days_in_future: int
):
    """
    Given:
        * A generated feed with zero or more entries and a future start date.
        * A fake LLM and date parser, with feed parsing kept offline.
    When:
        * Upcoming schedulable events are downloaded.
    Then:
        * One event is returned per feed entry with matching title, location,
        and start time.
    """
    start = datetime.datetime(2090, 1, 1) + datetime.timedelta(
        days=days_in_future
    )
    start_str = start.isoformat()
    feed_entries = [
        SimpleNamespace(
            title=title,
            link=link,
            content=[SimpleNamespace(value=description)],
        )
        for title, link, description in entries
    ]
    feed = SimpleNamespace(
        feed=SimpleNamespace(
            title="generated feed", link="https://example.com/feed"
        ),
        entries=feed_entries,
    )

    class FakeLLM:
        def create_chat_completion(self, **kwargs):
            properties = kwargs["response_format"]["schema"]["properties"]
            if "iso_datetime" in properties:
                content = {"iso_datetime": start_str}
            else:
                content = {"start": start_str, "end": ""}
            return {"choices": [{"message": {"content": json.dumps(content)}}]}

    downloader = utils.FeedEventDownloader(
        make_test_config(assume_schedulable_event=True),
        classifier=None,
        llm=FakeLLM(),
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(utils.feedparser, "parse", lambda feed_url: feed)
        monkeypatch.setattr(
            utils.dateparser,
            "parse",
            lambda value, settings: datetime.datetime.fromisoformat(value),
        )
        events = downloader.download_upcoming_schedulable_events(
            "https://example.com/feed"
        )

    assert len(events) == len(entries)
    assert [event["title"] for event in events] == [
        title for title, _, _ in entries
    ]
    for event, (_, link, _) in zip(events, entries):
        if "image_url" in event:
            assert event["online_locations[]"] == link
        else:
            assert event["online_locations"] == [link]
    assert all(
        event["start_datetime"] == int(start.timestamp()) for event in events
    )


@settings(max_examples=20)
@given(has_image=st.booleans(), title=st.text(max_size=80))
def test_send_event_to_gancio_handles_generated_payloads(
    has_image: bool, title: str
):
    """
    Given:
        * An event with a generated title and optional image URL.
    When:
        * The event is sent to Gancio.
    Then:
        * Exactly one POST is made, with an image GET and multipart payload only
        when needed.
    """
    response = SimpleNamespace(status_code=200, json=lambda: {})
    post_calls = []
    get_calls = []
    event = {"title": title, "start_datetime": 1}
    if has_image:
        event["image_url"] = "https://example.com/image.png"

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            utils.requests,
            "post",
            lambda *args, **kwargs: post_calls.append((args, kwargs))
            or response,
        )
        monkeypatch.setattr(
            utils.requests,
            "get",
            lambda *args, **kwargs: get_calls.append((args, kwargs))
            or SimpleNamespace(
                headers={"Content-Type": "image/png"}, content=b"image data"
            ),
        )
        GancioEventSender(
            "https://example.com/api/events"
        ).send_event_to_gancio(event)

    assert len(post_calls) == 1
    assert len(get_calls) == int(has_image)
    assert ("files" in post_calls[0][1]) is has_image
    assert ("json" in post_calls[0][1]) is (not has_image)


@settings(max_examples=30)
@given(
    items=st.lists(st.tuples(st.text(max_size=40), st.booleans()), max_size=6),
    interactive=st.booleans(),
)
def test_send_events_respects_generated_confirmation_choices(
    items, interactive: bool
):
    """
    Given:
        * Generated events with corresponding approval choices.
        * Interactive sending enabled or disabled.
    When:
        * The event list is sent.
    Then:
        * All events are sent when non-interactive; only approved events are
        sent otherwise.
    """
    sender = GancioEventSender("https://example.com/api/events")
    sent = []
    sender.send_event_to_gancio = sent.append
    confirmations = iter(approved for _, approved in items)
    events = [{"title": title} for title, _ in items]

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(utils.typer, "echo", lambda *args, **kwargs: None)
        monkeypatch.setattr(
            utils.typer, "confirm", lambda *args, **kwargs: next(confirmations)
        )
        sender.send_events_to_gancio(events, interactive=interactive)

    expected = [
        event
        for event, (_, approved) in zip(events, items)
        if not interactive or approved
    ]
    assert sent == expected
