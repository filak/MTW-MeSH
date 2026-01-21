import logging
from application.modules import utils as mtu


def configure_log(app, logname: str = "app"):

    if any(isinstance(h, logging.FileHandler) for h in app.logger.handlers):
        return

    if app.debug:
        level = logging.DEBUG
        log_file = mtu.get_instance_dir(app, f"logs/{logname}_debug.log")
    else:
        level = logging.INFO
        log_file = mtu.get_instance_dir(app, f"logs/{logname}.log")

    app.logger.setLevel(level)
    app.logger.propagate = False

    formatter = mtu.SafeFormatter("%(asctime)s - %(levelname)s: [%(ip)s] %(message)s")

    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setLevel(level)
    handler.setFormatter(formatter)
    handler.addFilter(mtu.RequestIPFilter())

    app.logger.addHandler(handler)
