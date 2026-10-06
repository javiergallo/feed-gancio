# FeedGancio

This document will guide you through the necessary steps to get FeedGancio up
and running.

## Description

Use FeedGancio to feed a Gancio instance with events from a RSS source, using
(sort of) a couple of intelligent language models that run locally.

## Getting Started

### Dependencies

* [Poetry](https://python-poetry.org/)

### Installing

First, go to the root directory and download Llama (this is hardcoded, which
means you won't be able to use another model... sorry):
```
cd feed-gancio/
wget https://huggingface.co/hugging-quants/Llama-3.2-3B-Instruct-Q8_0-GGUF/resolve/main/llama-3.2-3b-instruct-q8_0.gguf
```

Then:
```
poetry install
```

### Executing program

Go to the root directory:
```
cd feed-gancio/
```

Then, for an English feed, just pass feed URL followed by the Gancio instance URL:
```
PYTHONPATH=. poetry run typer feed-gancio.py run https://news.mit.edu/rss/feed https://vamosjuntes.com.ar/api/events/
```

For a Spanish feed, add an environment file:
```
PYTHONPATH=. poetry run typer feed-gancio.py run https://ffyh.unc.edu.ar/ciffyh/feed/ https://vamosjuntes.com.ar/api/events/ --env-file es.env
```

FeedGancio will do the best it can (it's not super smart) to detect and copy
schedulable events from the RSS source to the Gancio instance.

## Development

### Running tests

```
PYTHONPATH=. poetry run pytest
```

To show stdout:
```
PYTHONPATH=. poetry run pytest -s
```

## Help

TODO

## Authors

[Javier Gallo](https://github.com/javiergallo)

## License

TODO

## Acknowledgments

Everyone in [Mariconear.social](https://mariconear.social/about),
but specially [Sondra](https://mariconear.social/@Sondra).
