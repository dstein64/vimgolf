import datetime
import glob
import logging
import os
import sys
from enum import Enum

version_txt = os.path.join(os.path.dirname(__file__), 'version.txt')
with open(version_txt, 'r') as vf:
    __version__ = vf.read().strip()

# Enable ANSI terminal colors on Windows
if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes
    kernel32 = ctypes.windll.kernel32
    STD_OUTPUT_HANDLE = -11                   # https://docs.microsoft.com/en-us/windows/console/getstdhandle
    STD_ERROR_HANDLE = -12                    # ditto
    ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x4  # https://docs.microsoft.com/en-us/windows/console/getconsolemode
    for std_device in [STD_OUTPUT_HANDLE, STD_ERROR_HANDLE]:
        handle = kernel32.GetStdHandle(wintypes.DWORD(std_device))
        old_console_mode = wintypes.DWORD()
        kernel32.GetConsoleMode(handle, ctypes.byref(old_console_mode))
        new_console_mode = wintypes.DWORD(ENABLE_VIRTUAL_TERMINAL_PROCESSING | old_console_mode.value)
        kernel32.SetConsoleMode(handle, new_console_mode)

GOLF_HOST = os.environ.get('GOLF_HOST', 'https://www.vimgolf.com')
GOLF_VIM = os.environ.get('GOLF_VIM', 'vim')

RUBY_CLIENT_VERSION_COMPLIANCE = '0.4.8'

EXPANSION_PREFIX = '+'

USER_HOME = os.path.expanduser('~')

TIMESTAMP = datetime.datetime.utcnow().timestamp()

# Max number of listings by default for 'vimgolf list'
LISTING_LIMIT = 10

# Max number of leaders to show for 'vimgolf show'
LEADER_LIMIT = 3

# Max number of existing logs to retain
LOG_LIMIT = 10

# Max number of parallel web requests.
# As of 2018, most browsers use a max of six connections per hostname.
MAX_REQUEST_WORKERS = 6

PLAY_VIMRC_PATH = os.path.join(os.path.dirname(__file__), 'vimgolf.vimrc')

CONFIG_HOME = os.environ.get('XDG_CONFIG_HOME', os.path.join(USER_HOME, '.config'))
VIMGOLF_CONFIG_PATH = os.path.join(CONFIG_HOME, 'vimgolf')
os.makedirs(VIMGOLF_CONFIG_PATH, exist_ok=True)
VIMGOLF_API_KEY_PATH = os.path.join(VIMGOLF_CONFIG_PATH, 'api_key')

DATA_HOME = os.environ.get('XDG_DATA_HOME', os.path.join(USER_HOME, '.local', 'share'))
VIMGOLF_DATA_PATH = os.path.join(DATA_HOME, 'vimgolf')
os.makedirs(VIMGOLF_DATA_PATH, exist_ok=True)
VIMGOLF_ID_LOOKUP_PATH = os.path.join(VIMGOLF_DATA_PATH, 'id_lookup.json')

VIMGOLF_CHALLENGES_PATH = os.path.join(VIMGOLF_DATA_PATH, 'challenges')
os.makedirs(VIMGOLF_CHALLENGES_PATH, exist_ok=True)

CACHE_HOME = os.environ.get('XDG_CACHE_HOME', os.path.join(USER_HOME, '.cache'))
VIMGOLF_CACHE_PATH = os.path.join(CACHE_HOME, 'vimgolf')
os.makedirs(VIMGOLF_CACHE_PATH, exist_ok=True)

VIMGOLF_LOG_DIR_PATH = os.path.join(VIMGOLF_CACHE_PATH, 'log')
os.makedirs(VIMGOLF_LOG_DIR_PATH, exist_ok=True)
VIMGOLF_LOG_FILENAME = 'vimgolf-{}-{}.log'.format(TIMESTAMP, os.getpid())
VIMGOLF_LOG_PATH = os.path.join(VIMGOLF_LOG_DIR_PATH, VIMGOLF_LOG_FILENAME)

logger = logging.getLogger('vimgolf')

# Initialize logger
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(VIMGOLF_LOG_PATH, mode='w')
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.info('vimgolf started')

# Clean stale logs
logger.info('cleaning stale logs')
existing_logs_glob = os.path.join(VIMGOLF_LOG_DIR_PATH, 'vimgolf-*-*.log')
existing_logs = glob.glob(existing_logs_glob)
log_sort_key = lambda x: float(os.path.basename(x).split('-')[1])
stale_existing_logs = sorted(existing_logs, key=log_sort_key)[:-LOG_LIMIT]
for log in stale_existing_logs:
    logger.info('deleting stale log: {}'.format(log))
    try:
        os.remove(log)
    except Exception:
        logger.exception('error deleting stale log: {}'.format(log))


class Status(Enum):
    SUCCESS = 1
    FAILURE = 2


EXIT_SUCCESS = 0
EXIT_FAILURE = 1
