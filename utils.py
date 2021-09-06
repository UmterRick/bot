import json
import os
import logging
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def read_config(config_json_filename):
    path = ROOT_DIR + '/configs/' + config_json_filename
    with open(path) as config_json:
        config = json.load(config_json)
        return config


def set_logger(logger_name) -> logging.Logger:
    logger_config = read_config('loggers.json')

    levels = {'ERROR': logging.ERROR,
              'WARNING': logging.WARNING,
              'INFO': logging.INFO,
              'DEBUG': logging.DEBUG
              }
    logger_config = logger_config.get(logger_name, '')

    logger = logging.getLogger(logger_name)

    c_handler = logging.StreamHandler()
    f_handler = logging.FileHandler(ROOT_DIR + f'/log/{logger_config.get("file")}')
    c_handler.setLevel(levels.get(logger_config.get('level')))
    f_handler.setLevel(levels.get(logger_config.get('level')))
    # Create formatters and add it to handlers
    c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    f_format = logging.Formatter('%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s')

    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)
    # Add handlers to the logger
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    return logger

def create_callback_data(*args):
    data = []
    for arg in args:
        data.append(str(arg))
    res = ';'.join(data)
    return res


def separate_callback_data(data):
    return data.split(";")

set_logger('database')