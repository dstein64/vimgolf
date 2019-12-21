import os
import re
import sys

from vimgolf import VIMGOLF_API_KEY_PATH
from vimgolf.utils import write


def validate_api_key(api_key):
    return api_key is not None and re.match(r'[\w\d]{32}', api_key)


def get_api_key():
    if not os.path.exists(VIMGOLF_API_KEY_PATH):
        return None
    with open(VIMGOLF_API_KEY_PATH, 'r') as f:
        return f.read()


def set_api_key(api_key):
    with open(VIMGOLF_API_KEY_PATH, 'w') as f:
        f.write(api_key)


def show_api_key_help():
    write('An API key can be obtained from vimgolf.com', color='yellow')
    write('Please run "vimgolf config API_KEY" to set your API key', color='yellow')


def show_api_key_error():
    write('Invalid API key', stream=sys.stderr, color='red')
    write('Please check your API key on vimgolf.com', stream=sys.stderr, color='red')
