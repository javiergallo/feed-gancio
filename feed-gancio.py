import locale
import typer

from typing import Annotated

from feed_gancio.models import load_models
from feed_gancio.utils import (
    download_upcoming_schedulable_events,
    send_events_to_gancio,
)
from feed_gancio.settings import Config


def main(
    feed_url: str,
    gancio_url: str,
    env_file: Annotated[str, typer.Option()] = None,
):
    config = Config() if env_file is None else Config(_env_file=env_file)

    if config.locale is not None:
        locale.setlocale(locale.LC_TIME, config.locale)

    classifier, llm = load_models(
        prompt_context_max_length=config.prompt_context_max_length
    )
    upcoming_schedulable_events = download_upcoming_schedulable_events(
        config, classifier, llm, feed_url
    )
    send_events_to_gancio(
        upcoming_schedulable_events, gancio_url, interactive=True
    )


if __name__ == "__main__":
    typer.run(main)
