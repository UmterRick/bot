import json
import os
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def read_config(config_json_filename):
    path = ROOT_DIR + '/configs/' + config_json_filename
    with open(path) as config_json:
        config = json.load(config_json)
        return config


def create_callback_data(*args):
    data = []
    for arg in args:
        data.append(str(arg))
    res = ';'.join(data)
    return res


def separate_callback_data(data):
    return data.split(";")

