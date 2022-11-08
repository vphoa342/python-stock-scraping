import json
import os
import sys

import numpy as np

STOP_SIGNAL = False


def get_data_folder() -> str:
    # with open(resource_path('setting/setting.json'), 'r') as file:
    #     return json.load(file)['data_folder']
    return './data'


def resource_path(relative_path) -> str:
    application_path = ""
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    elif __file__:
        application_path = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(application_path, relative_path))


def get_email_config() -> dict:
    with open(get_data_folder() + '/config.json', 'r') as f:
        return json.load(f)


def get_old_data() -> dict:
    with open(get_data_folder() + '/data.json', 'r') as f:
        return json.load(f)


def get_stock_list() -> list:
    with open(get_data_folder() + '/data.txt', 'r') as f:
        return f.read().splitlines()


def save_error_log(message) -> None:
    with open(get_data_folder() + '/error.txt', 'a') as f:
        f.write(message + "\n")


class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)


def save_data_json(stocks: dict) -> None:
    # WRITE DATA TO FILE
    try:
        with open(get_data_folder() + "/data.json", "w") as f:
            json.dump(stocks, cls=NpEncoder, fp=f)
            print("save to file successfully")
    except Exception:
        print("save to file failed")
        stocks = {'default': {}}
        json.dump(stocks, f)


def get_oauth2_json() -> dict:
    """
    open file oauth2.json in data folder
    :return: dict: file json
    """

    with open(get_data_folder() + "/oauth2.json", "r") as file:
        return json.load(file)
