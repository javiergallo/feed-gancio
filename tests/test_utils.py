import feedparser
import locale
import os
import pytest

from feed_gancio.models import load_models
from feed_gancio.utils import download_upcoming_schedulable_events
from feed_gancio.settings import Config


@pytest.mark.parametrize("n_upcoming_events", [0, 1, 2])
def test_download_upcoming_events(n_upcoming_events: int):
    config = Config(_env_file="es.env")

    if config.locale is not None:
        locale.setlocale(locale.LC_TIME, config.locale)

    classifier, llm = load_models(
        prompt_context_max_length=config.prompt_context_max_length
    )

    cur_dir_path = os.path.dirname(os.path.abspath(__file__))
    events_data = download_upcoming_schedulable_events(
        config,
        classifier,
        llm,
        feed_url=f"{cur_dir_path}/test-feed-{n_upcoming_events}.xml",
    )

    assert isinstance(events_data, list)
    assert len(events_data) == n_upcoming_events
    for event_data in events_data:
        assert isinstance(event_data, dict)
