import sys
import time
import asyncio
import logging
import calendar
import requests
import linecache

from datetime import datetime, timedelta

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram import executor, Dispatcher, Bot
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Update

TOKEN = '1485443475:AAEv-Xl15Xp9Z6sSFyH4tizumu4oeJ3ZtdY'
ADMIN_PASSWORD = '1111'
TRAINER_PASSWORD = '2222'
LOG_PASSWORD = '3333'

HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:85.0) Gecko/20100101 Firefox/85.0'}
URL = 'https://meandmyschool.org.ua/ru/'
C_URL = 'https://meandmyschool.org.ua/detalnishe-pro-prohramy/'

DB_NAME = 'test1'

host = '127.0.0.1'
port = '3306'
db_user = 'root'
db_passwd = 'root'


DELAY = 10
DELAY_2 = 30

# webhook settings
WEBHOOK_HOST = 'https://your.domain'
WEBHOOK_PATH = ''
WEBHOOK_URL = 'https://6170de51ab69.ngrok.io'.strip()

# webserver settings
WEBAPP_HOST = 'localhost'  # or ip
WEBAPP_PORT = 8080

weekdays = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС']
eng_weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
daytimes = []


def str_to_list(input_str):
    res = list()
    try:
        if input_str == '' or input_str == '[]' or input_str is None:
            res = list()
        else:
            if input_str.startswith('[') and input_str.endswith(']') and len(input_str) > 2:
                input_str = input_str[1:-1]
            for i in input_str.split(','):
                i = int(i.strip())
                res.append(i)
    except ValueError:
        res = []
        print(f'ERROR wrong input in string to list transformation: {input_str, type(input_str)}')
    except AttributeError:
        res = []
        print(f'ERROR argument must be string: {input_str, type(input_str)}')
    except TypeError:
        res = []
        print(f'ERROR argument must be string: {input_str, type(input_str)}')
    except:
        res = []
        print('Unknown ERROR')
    finally:
        return res


def create_callback_data(*args):
    data = []
    for arg in args:
        data.append(str(arg))
    res = ';'.join(data)
    return res


def separate_callback_data(data):
    return data.split(";")


def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    exc = 'EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj)
    print(exc)
    return exc

