import logging
import os


LOG_FMT = "%(asctime)s, %(levelname)s, %(message)s"


def configure_script_logging(logger, script_path):
    resolved_script_path = os.path.realpath(script_path)
    base_folder = os.path.dirname(resolved_script_path)
    base_filename = os.path.splitext(os.path.basename(resolved_script_path))[0]
    log_file = os.path.join(base_folder, "{}.log".format(base_filename))

    try:
        os.remove(log_file)
    except FileNotFoundError:
        pass

    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        handler.close()

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    logging.basicConfig(
        level=logging.INFO,
        filename=log_file,
        filemode="w",
        format=LOG_FMT,
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_FMT))
    logger.addHandler(console_handler)
    return log_file