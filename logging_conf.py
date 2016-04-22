#!/usr/env/bin python
# coding=utf8


def get_logging_conf_json(log_file_path=None, debug=False):
    log_level = "DEBUG"
    conf = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {
                "format": "%(levelname)s %(asctime)s [%(name)s]:\t %(message)s"
            },
            "detailed": {
                "format": "%(levelname)s %(asctime)s [%(module)s:%(lineno)d] (%(process)d:%(thread)d)\t %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "detailed",
                "stream": "ext://sys.stdout"
            },
        },
        "root": {
                "level": "ERROR",
                "handlers": ["info_file_handler"]
        }
    }

    if log_file_path:
        conf['handlers']['info_file_handler'] = {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "level": log_level,
            "formatter": "simple",
            "filename": log_file_path,
            "when": "midnight",
            "backupCount": 30,
            "encoding": "utf8"
        }

    return conf