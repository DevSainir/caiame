import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)


def get_logger(name: str) -> logging.Logger:
    """A named logger. Messages are English, like the rest of the code."""
    return logging.getLogger(name)
