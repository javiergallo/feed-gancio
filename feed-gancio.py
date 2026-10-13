import locale
import typer

from typing import Annotated

from feed_gancio.models import load_models
from feed_gancio.utils import FeedEventDownloader, GancioEventSender
from feed_gancio.settings import Config


def main(
    feed_url: str,
    gancio_url: str,
    env_file: Annotated[str, typer.Option()] = None,
):
    config = Config() if env_file is None else Config(_env_file=env_file)

    if config.locale is not None:
        locale.setlocale(locale.LC_TIME, config.locale)

    classifier, llm = load_models(config)
    feed_downloader = FeedEventDownloader(config, classifier, llm)
    events = feed_downloader.download_upcoming_schedulable_events(feed_url)

    event_sender = GancioEventSender(gancio_url)
    event_sender.send_events_to_gancio(events, interactive=True)


if __name__ == "__main__":
    typer.run(main)
