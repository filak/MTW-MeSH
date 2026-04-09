import logging
from flask import has_request_context, request
from application.modules.utils import get_instance_dir


class SafeFormatter(logging.Formatter):
    """A custom formatter to safely handle missing attributes."""

    def format(self, record):
        if "ip" not in record.__dict__:
            record.ip = "N/A"
        return super().format(record)


class RequestIPFilter(logging.Filter):
    def __init__(self, max_len=15):
        super().__init__()
        self.max_len = max_len

    def filter(self, record):
        if has_request_context():
            record.ip = request.remote_addr or "None"
        else:
            record.ip = "N/A"
        # record.ip = record.ip.ljust(self.max_len)
        return True


def configure_log(app, logname: str = "app"):

    # Avoid duplicate setup
    app.logger.handlers.clear()
    app.logger.propagate = False

    is_dev = app.debug

    level = logging.DEBUG if is_dev else logging.INFO

    log_file = get_instance_dir(
        app, f"logs/{logname}_debug.log" if is_dev else f"logs/{logname}.log"
    )

    formatter = SafeFormatter("%(asctime)s - %(levelname)s: [%(ip)s] %(message)s")

    # --- File handler (always) ---
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(RequestIPFilter())

    app.logger.addHandler(file_handler)

    # --- Console handler (dev only) ---
    if is_dev:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(RequestIPFilter())

        app.logger.addHandler(console_handler)

    # Set overall logger level
    app.logger.setLevel(level)
