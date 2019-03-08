from collections import namedtuple
import concurrent.futures
import datetime
from distutils.version import StrictVersion
from enum import Enum
import filecmp
import glob
import json
import logging.handlers
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

from vimgolf.html import (
    get_elements_by_classname,
    get_element_by_id,
    get_elements_by_tagname,
    get_text,
    NodeType,
    parse_html,
)
from vimgolf.keys import (
    get_keycode_repr,
    IGNORED_KEYSTROKES,
    parse_keycodes,
)


version_txt = os.path.join(os.path.dirname(__file__), 'version.txt')
with open(version_txt, 'r') as f:
    __version__ = f.read().strip()


class Status(Enum):
    SUCCESS = 1
    FAILURE = 2


EXIT_SUCCESS = 0
EXIT_FAILURE = 1


# ************************************************************
# * Environment
# ************************************************************

# Enable ANSI terminal colors on Windows
if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes
    kernel32 = ctypes.windll.kernel32
    STD_OUTPUT_HANDLE = -11                  # https://docs.microsoft.com/en-us/windows/console/getstdhandle
    STD_ERROR_HANDLE = -12                   # ditto
    ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x4 # https://docs.microsoft.com/en-us/windows/console/getconsolemode
    for std_device in [STD_OUTPUT_HANDLE, STD_ERROR_HANDLE]:
        handle = kernel32.GetStdHandle(wintypes.DWORD(std_device))
        old_console_mode = wintypes.DWORD()
        kernel32.GetConsoleMode(handle, ctypes.byref(old_console_mode))
        new_console_mode = wintypes.DWORD(ENABLE_VIRTUAL_TERMINAL_PROCESSING | old_console_mode.value)
        kernel32.SetConsoleMode(handle, new_console_mode)


# ************************************************************
# * Configuration, Global Variables, and Logging
# ************************************************************

GOLF_HOST = os.environ.get('GOLF_HOST', 'https://www.vimgolf.com')
GOLF_VIM = os.environ.get('GOLF_VIM', 'vim')

USER_AGENT = 'vimgolf'

RUBY_CLIENT_VERSION_COMPLIANCE = '0.4.8'

EXPANSION_PREFIX='+'

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

CONFIG_HOME = os.environ.get('XDG_CONFIG_HOME', os.path.join(USER_HOME, '.config'))
VIMGOLF_CONFIG_PATH = os.path.join(CONFIG_HOME, 'vimgolf')
os.makedirs(VIMGOLF_CONFIG_PATH, exist_ok=True)
VIMGOLF_API_KEY_FILENAME = 'api_key'

DATA_HOME = os.environ.get('XDG_DATA_HOME', os.path.join(USER_HOME, '.local', 'share'))
VIMGOLF_DATA_PATH = os.path.join(DATA_HOME, 'vimgolf')
os.makedirs(VIMGOLF_DATA_PATH, exist_ok=True)
VIMGOLF_ID_LOOKUP_FILENAME = 'id_lookup.json'

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


# ************************************************************
# * Utils
# ************************************************************

HttpResponse = namedtuple('HttpResponse', 'code msg headers body')


def http_request(url, data=None):
    request = urllib.request.Request(url, data, headers={'User-Agent': USER_AGENT})
    response = urllib.request.urlopen(request)
    try:
        charset = response.getheader('Content-Type').split(';')[1].split('=')[1].strip()
    except Exception:
        charset = 'utf-8'
    body = response.read().decode(charset)
    output = HttpResponse(
        code=response.code, msg=response.msg, headers=response.getheaders(), body=body)
    return output


def join_lines(string):
    lines = [line.strip() for line in string.split('\n') if line]
    return ' '.join(lines)


def write(string, end='\n', stream=None, color=None):
    string = str(string)
    color_lookup = {
        'red':     '\033[31m',
        'green':   '\033[32m',
        'yellow':  '\033[33m',
        'blue':    '\033[34m',
        'magenta': '\033[35m',
        'cyan':    '\033[36m',
    }
    end_color = '\033[0m'
    if color and color not in color_lookup:
        raise RuntimeError('Unavailable color: {}'.format(color))
    if stream is None:
        stream = sys.stdout
    if color and hasattr(stream, 'isatty') and stream.isatty():
        string = color_lookup[color] + string + end_color
    stream.write(string)
    if end is not None:
        stream.write(str(end))
    stream.flush()


def format_(string):
    """dos2unix and add newline to end if missing."""
    string = string.replace('\r\n', '\n').replace('\r', '\n')
    if not string.endswith('\n'):
        string = string + '\n'
    return string


def input_loop(prompt, strip=True, required=True):
    try:
        import readline
    except Exception:
        pass
    while True:
        try:
            selection = input(prompt)
            if strip:
                selection = selection.strip()
        except EOFError:
            write('', stream=sys.stderr)
            sys.exit(EXIT_FAILURE)
        except KeyboardInterrupt:
            write('', stream=sys.stderr)
            write('KeyboardInterrupt', stream=sys.stderr)
            continue
        if required and not selection:
            continue
        break
    return selection


def confirm(prompt):
    while True:
        selection = input_loop('{} [y/n] '.format(prompt)).lower()
        if selection in ('y', 'yes'):
            break
        elif selection in ('n', 'no'):
            return False
        else:
            write('Invalid selection: {}'.format(selection), stream=sys.stdout, color='red')
    return True


def find_executable_unix(executable):
    if os.path.isfile(executable):
        return executable
    paths = os.environ.get('PATH', os.defpath).split(os.pathsep)
    for p in paths:
        f = os.path.join(p, executable)
        if os.path.isfile(f):
            return f
    return None


def find_executable_win32(executable):
    """Emulates how cmd.exe seemingly searches for executables."""
    def fixcase(p):
        return str(Path(p).resolve())
    pathext = os.environ.get('PATHEXT', '.EXE')
    pathexts = list(x.upper() for x in pathext.split(os.pathsep))
    _, ext = os.path.splitext(executable)
    if os.path.isfile(executable) and ext.upper() in pathexts:
        return fixcase(executable)
    for x in pathexts:
        if os.path.isfile(executable + x):
            return fixcase(executable + x)
    if executable != os.path.basename(executable):
        return None
    paths = os.environ.get('PATH', os.defpath).split(os.pathsep)
    for p in paths:
        candidate = os.path.join(p, executable)
        if os.path.isfile(candidate) and ext.upper() in pathexts:
            return fixcase(candidate)
        for x in pathexts:
            if os.path.isfile(candidate + x):
                return fixcase(candidate + x)
    return None


def find_executable(executable):
    if sys.platform == 'win32':
        return find_executable_win32(executable)
    else:
        return find_executable_unix(executable)


# ************************************************************
# * Core
# ************************************************************

def validate_challenge_id(challenge_id):
    return challenge_id is not None and re.match(r'[\w\d]{24}', challenge_id)


def show_challenge_id_error():
    write('Invalid challenge ID', stream=sys.stderr, color='red')
    write('Please check the ID on vimgolf.com', stream=sys.stderr, color='red')


def validate_api_key(api_key):
    return api_key is not None and re.match(r'[\w\d]{32}', api_key)


def get_api_key():
    api_key_path = os.path.join(VIMGOLF_CONFIG_PATH, VIMGOLF_API_KEY_FILENAME)
    if not os.path.exists(api_key_path):
        return None
    with open(api_key_path, 'r') as f:
        api_key = f.read()
        return api_key


def set_api_key(api_key):
    api_key_path = os.path.join(VIMGOLF_CONFIG_PATH, VIMGOLF_API_KEY_FILENAME)
    with open(api_key_path, 'w') as f:
        f.write(api_key)


def show_api_key_help():
    write('An API key can be obtained from vimgolf.com', color='yellow')
    write('Please run "vimgolf config API_KEY" to set your API key', color='yellow')


def show_api_key_error():
    write('Invalid API key', stream=sys.stderr, color='red')
    write('Please check your API key on vimgolf.com', stream=sys.stderr, color='red')


def get_id_lookup():
    id_lookup_path = os.path.join(VIMGOLF_DATA_PATH, VIMGOLF_ID_LOOKUP_FILENAME)
    id_lookup = {}
    if os.path.exists(id_lookup_path):
        with open(id_lookup_path, 'r') as f:
            id_lookup = json.load(f)
    return id_lookup


def set_id_lookup(id_lookup):
    id_lookup_path = os.path.join(VIMGOLF_DATA_PATH, VIMGOLF_ID_LOOKUP_FILENAME)
    with open(id_lookup_path, 'w') as f:
        json.dump(id_lookup, f, indent=2)


def expand_challenge_id(challenge_id):
    if challenge_id.startswith(EXPANSION_PREFIX):
        challenge_id = get_id_lookup().get(challenge_id[1:], challenge_id)
    return challenge_id


def get_challenge_url(challenge_id):
    return urllib.parse.urljoin(GOLF_HOST, '/challenges/{}'.format(challenge_id))


Challenge = namedtuple('Challenge', [
    'in_text',
    'out_text',
    'in_extension',
    'out_extension',
    'id',
    'compliant',
    'api_key'
])


def upload_result(challenge_id, api_key, raw_keys):
    logger.info('upload_result(...)')
    status = Status.FAILURE
    try:
        url = urllib.parse.urljoin(GOLF_HOST, '/entry.json')
        data_dict = {
            'challenge_id': challenge_id,
            'apikey':       api_key,
            'entry':        raw_keys,
        }
        data = urllib.parse.urlencode(data_dict).encode()
        response = http_request(url, data=data)
        message = json.loads(response.body)
        if message.get('status') == 'ok':
            status = Status.SUCCESS
    except Exception:
        logger.exception('upload failed')
    return status


def play(challenge, workspace):
    logger.info('play(...)')

    vim_path = find_executable(GOLF_VIM)
    if not vim_path:
        write('Unable to find "{}"'.format(GOLF_VIM), color='red')
        write('Please update your PATH to include the directory with "{}"'.format(GOLF_VIM), color='red')
        return Status.FAILURE
    vim_name = os.path.basename(os.path.realpath(vim_path))

    if sys.platform == 'win32':
        # Remove executable extension (.exe, .bat, .cmd, etc.) from 'vim_name'
        base, ext = os.path.splitext(vim_name)
        pathexts = os.environ.get('PATHEXT', '.EXE').split(os.pathsep)
        for pathext in pathexts:
            if ext.upper() == pathext.upper():
                vim_name = base
                break

    # As of 2019/3/2, on Windows, nvim-qt doesn't support --nofork.
    # Issue a warning as opposed to failing, since this may change.
    if vim_name == 'nvim-qt' and sys.platform == 'win32':
        write('vimgolf with nvim-qt on Windows may not function properly', color='red')
        write('If there are issues, please try using a different version of vim', color='yellow')
        if not confirm('Continue trying to play?'):
            return Status.FAILURE

    def vim(args, **run_kwargs):
        # Configure args used by all vim invocations (for both playing and diffing)
        # 'vim_path' is used instead of GOLF_VIM to handle 'vim.bat' on the PATH.
        # subprocess.run would not launch vim.bat with GOLF_VIM == 'vim', but 'find_executable'
        # will return the full path to vim.bat in that case.
        vim_args = [vim_path]
        # Add --nofork so gvim, mvim, and nvim-qt don't return immediately
        # Add special-case handling since nvim doesn't accept that option.
        if vim_name != 'nvim':
            vim_args.append('--nofork')
        # For nvim-qt, options after '--' are passed to nvim.
        if vim_name == 'nvim-qt':
            vim_args.append('--')
        vim_args.extend(args)
        subprocess.run(vim_args, **run_kwargs)
        # On Windows, vimgolf freezes when reading input after nvim's exit.
        # For an unknown reason, shell'ing out an effective no-op works-around the issue
        if vim_name == 'nvim' and sys.platform == 'win32':
            os.system('')

    infile = os.path.join(workspace, 'in')
    if challenge.in_extension:
        infile += challenge.in_extension
    outfile = os.path.join(workspace, 'out')
    if challenge.out_extension:
        outfile += challenge.out_extension
    logfile = os.path.join(workspace, 'log')
    with open(outfile, 'w') as f:
        f.write(challenge.out_text)

    write('Launching vimgolf session', color='yellow')
    while True:
        with open(infile, 'w') as f:
            f.write(challenge.in_text)

        vimrc = os.path.join(os.path.dirname(__file__), 'vimgolf.vimrc')
        play_args = [
            '-Z',          # restricted mode, utilities not allowed
            '-n',          # no swap file, memory only editing
            '--noplugin',  # no plugins
            '-i', 'NONE',  # don't load .viminfo (e.g., has saved macros, etc.)
            '+0',          # start on line 0
            '-u', vimrc,   # vimgolf .vimrc
            '-U', 'NONE',  # don't load .gvimrc
            '-W', logfile, # keylog file (overwrites existing)
            infile,
        ]
        try:
            vim(play_args, check=True)
        except Exception:
            logger.exception('{} execution failed'.format(GOLF_VIM))
            write('The execution of {} has failed'.format(GOLF_VIM), stream=sys.stderr, color='red')
            return Status.FAILURE

        correct = filecmp.cmp(infile, outfile)
        with open(logfile, 'rb') as _f:
            # raw keypress representation saved by vim's -w
            raw_keys = _f.read()

        # list of parsed keycode byte strings
        keycodes = parse_keycodes(raw_keys)
        keycodes = [keycode for keycode in keycodes if keycode not in IGNORED_KEYSTROKES]

        # list of human-readable key strings
        keycode_reprs = [get_keycode_repr(keycode) for keycode in keycodes]

        score = len(keycodes)

        write('Here are your keystrokes:', color='green')
        for keycode_repr in keycode_reprs:
            color = 'magenta' if len(keycode_repr) > 1 else None
            write(keycode_repr, color=color, end=None)
        write('')

        if correct:
            write('Success! Your output matches.', color='green')
            write('Your score:', color='green')
        else:
            write('Uh oh, looks like your entry does not match the desired output.', color='red')
            write('Your score for this failed attempt:', color='red')
        write(score)

        upload_eligible = challenge.id and challenge.compliant and challenge.api_key

        while True:
            # Generate the menu items inside the loop since it can change across iterations
            # (e.g., upload option can be removed)
            menu = []
            if not correct:
                menu.append(('d', 'Show diff'))
            if upload_eligible and correct:
                menu.append(('w', 'Upload result'))
            menu.append(('r', 'Retry the current challenge'))
            menu.append(('q', 'Quit vimgolf'))
            valid_codes = [x[0] for x in menu]
            for option in menu:
                write('[{}] {}'.format(*option), color='yellow')
            selection = input_loop('Choice> ')
            if selection not in valid_codes:
                write('Invalid selection: {}'.format(selection), stream=sys.stderr, color='red')
            elif selection == 'd':
                diff_args = ['-d', '-n', infile, outfile]
                vim(diff_args)
            elif selection == 'w':
                upload_status = upload_result(challenge.id, challenge.api_key, raw_keys)
                if upload_status == Status.SUCCESS:
                    write('Uploaded entry!', color='green')
                    leaderboard_url = get_challenge_url(challenge.id)
                    write('View the leaderboard: {}'.format(leaderboard_url), color='green')
                    upload_eligible = False
                else:
                    write('The entry upload has failed', stream=sys.stderr, color='red')
                    message = 'Please check your API key on vimgolf.com'
                    write(message, stream=sys.stderr, color='red')
            else:
                break
        if selection == 'q':
            break
        write('Retrying vimgolf challenge', color='yellow')

    write('Thanks for playing!', color='green')
    return Status.SUCCESS


def local(infile, outfile):
    logger.info('local(%s, %s)', infile, outfile)
    with open(infile, 'r') as f:
        in_text = format_(f.read())
    with open(outfile, 'r') as f:
        out_text = format_(f.read())
    _, in_extension = os.path.splitext(infile)
    _, out_extension = os.path.splitext(outfile)
    challenge = Challenge(
        in_text=in_text,
        out_text=out_text,
        in_extension=in_extension,
        out_extension=out_extension,
        id=None,
        compliant=None,
        api_key=None)
    with tempfile.TemporaryDirectory() as d:
        status = play(challenge, d)
    return status


def put(challenge_id):
    challenge_id = expand_challenge_id(challenge_id)
    logger.info('put(%s)', challenge_id)
    if not validate_challenge_id(challenge_id):
        show_challenge_id_error()
        return Status.FAILURE
    api_key = get_api_key()
    if not validate_api_key(api_key):
        write('An API key has not been configured', color='red')
        write('Uploading to vimgolf.com is disabled', color='red')
        show_api_key_help()
        if not confirm('Play without uploads?'):
            return Status.FAILURE

    try:
        write('Downloading vimgolf challenge {}'.format(challenge_id), color='yellow')
        url = urllib.parse.urljoin(GOLF_HOST, '/challenges/{}.json'.format(challenge_id))
        response = http_request(url)
        challenge_spec = json.loads(response.body)
        compliant = challenge_spec.get('client') == RUBY_CLIENT_VERSION_COMPLIANCE
        if not compliant:
            message = 'vimgolf=={} is not compliant with vimgolf.com'.format(__version__)
            write(message, stream=sys.stderr, color='red')
            write('Uploading to vimgolf.com is disabled', stream=sys.stderr, color='red')
            write('vimgolf may not function properly', color='red')
            try:
                client_compliance_version = StrictVersion(RUBY_CLIENT_VERSION_COMPLIANCE)
                api_version = StrictVersion(challenge_spec['client'])
                action = 'upgrade' if api_version > client_compliance_version else 'downgrade'
            except Exception:
                action = 'update'
            write('Please {} vimgolf to a compliant version'.format(action), color='yellow')
            if not confirm('Try to play without uploads?'):
                return Status.FAILURE

        in_text = format_(challenge_spec['in']['data'])
        out_text = format_(challenge_spec['out']['data'])
        in_type = challenge_spec['in']['type']
        out_type = challenge_spec['out']['type']
        # Sanitize and add leading dot
        in_extension = '.{}'.format(re.sub(r'[^\w-]', '_', in_type))
        out_extension = '.{}'.format(re.sub(r'[^\w-]', '_', out_type))
    except Exception:
        logger.exception('challenge retrieval failed')
        write('The challenge retrieval has failed', stream=sys.stderr, color='red')
        write('Please check the challenge ID on vimgolf.com', stream=sys.stderr, color='red')
        return Status.FAILURE

    challenge = Challenge(
        in_text=in_text,
        out_text=out_text,
        in_extension=in_extension,
        out_extension=out_extension,
        id=challenge_id,
        compliant=compliant,
        api_key=api_key)
    with tempfile.TemporaryDirectory() as d:
        status = play(challenge, d)

    return status


def list_(page=None, limit=LISTING_LIMIT):
    logger.info('list_(%s, %s)', page, limit)
    Listing = namedtuple('Listing', 'id name n_entries')
    try:
        listings = []
        url = GOLF_HOST
        if page is not None:
            url = urllib.parse.urljoin(GOLF_HOST, '/?page={}'.format(page))
        response = http_request(url)
        nodes = parse_html(response.body)
        challenge_elements = get_elements_by_classname(nodes, 'challenge')
        for element in challenge_elements:
            if len(listings) >= limit:
                break
            id_, name, n_entries = None, None, None
            anchor = get_elements_by_tagname(element.children, 'a')[0]
            href = anchor.get_attr('href')
            id_ = href.split('/')[-1]
            name = anchor.children[0].data
            for child in element.children:
                if child.node_type == NodeType.TEXT and 'entries' in child.data:
                    n_entries = int([x for x in child.data.split() if x.isdigit()][0])
                    break
            listing = Listing(id=id_, name=name, n_entries=n_entries)
            listings.append(listing)
    except Exception:
        logger.exception('challenge retrieval failed')
        write('The challenge list retrieval has failed', stream=sys.stderr, color='red')
        return Status.FAILURE

    for idx, listing in enumerate(listings):
        write('{}{} '.format(EXPANSION_PREFIX, idx + 1), end=None)
        write('{} - {} entries ('.format(listing.name, listing.n_entries), end=None)
        write(listing.id, color='yellow', end=None)
        write(')')

    id_lookup = {str(idx+1): listing.id for idx, listing in enumerate(listings)}
    set_id_lookup(id_lookup)

    return Status.SUCCESS


def show(challenge_id):
    challenge_id = expand_challenge_id(challenge_id)
    logger.info('show(%s)', challenge_id)
    try:
        if not validate_challenge_id(challenge_id):
            show_challenge_id_error()
            return Status.FAILURE
        api_url = urllib.parse.urljoin(GOLF_HOST, '/challenges/{}.json'.format(challenge_id))
        page_url = get_challenge_url(challenge_id)
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_REQUEST_WORKERS) as executor:
            results = executor.map(http_request, [api_url, page_url])
            api_response = next(results)
            page_response = next(results)
        challenge_spec = json.loads(api_response.body)
        start_file = challenge_spec['in']['data']
        if not start_file.endswith('\n'):
            start_file += '\n'
        end_file = challenge_spec['out']['data']
        if not end_file.endswith('\n'):
            end_file += '\n'
        nodes = parse_html(page_response.body)
        content_element = get_element_by_id(nodes, 'content')
        content_grid_7_element = get_elements_by_classname(content_element.children, 'grid_7')[0]
        name_h3 = get_elements_by_tagname(content_grid_7_element.children, 'h3')[0]
        name = join_lines(get_text([name_h3]).strip())
        description_p_element = get_elements_by_tagname(content_grid_7_element.children, 'p')[0]
        description = join_lines(get_text([description_p_element]).strip())
        content_grid_5_element = get_elements_by_classname(content_element.children, 'grid_5')[0]
        Leader = namedtuple('Leader', 'username score')
        leaders = []
        leaderboard_divs = get_elements_by_tagname(content_grid_5_element.children, 'div')
        for leaderboard_div in leaderboard_divs:
            user_h6 = get_elements_by_tagname(leaderboard_div.children, 'h6')[0]
            username_anchor = get_elements_by_tagname(user_h6.children, 'a')[1]
            username = get_text([username_anchor]).strip()
            if username.startswith('@'):
                username = username[1:]
            score_div = get_elements_by_tagname(leaderboard_div.children, 'div')[0]
            score = int(get_text([score_div]).strip())
            leader = Leader(username=username, score=score)
            leaders.append(leader)
        separator = '-' * 50
        write(separator)
        write('{} ('.format(name), end=None)
        write(challenge_id, color='yellow', end=None)
        write(')')
        write(separator)
        write(page_url)
        write(separator)
        write('Leaderboard', color='green')
        if leaders:
            for leader in leaders[:LEADER_LIMIT]:
                write('{} {}'.format(leader.username.ljust(15), leader.score))
            if len(leaders) > LEADER_LIMIT:
                write('...')
        else:
            write('no entries yet', color='yellow')
        write(separator)
        write(description)
        write(separator)
        write('Start File', color='green')
        write(start_file, end=None)
        write(separator)
        write('End File', color='green')
        write(end_file, end=None)
        write(separator)
    except Exception:
        logger.exception('challenge retrieval failed')
        write('The challenge retrieval has failed', stream=sys.stderr, color='red')
        write('Please check the challenge ID on vimgolf.com', stream=sys.stderr, color='red')
        return Status.FAILURE

    return Status.SUCCESS


def config(api_key=None):
    logger.info('config(...)')
    if api_key is not None and not validate_api_key(api_key):
        show_api_key_error()
        return Status.FAILURE

    if api_key:
        set_api_key(api_key)
        return Status.SUCCESS

    api_key = get_api_key()
    if api_key:
        write(api_key)
    else:
        show_api_key_help()

    return Status.SUCCESS


# ************************************************************
# * Command Line Interface
# ************************************************************

def main(argv=sys.argv):
    logger.info('main(%s)', argv)
    if len(argv) < 2:
        command = 'help'
    else:
        command = argv[1]

    help_message = (
        'Commands:\n'
        '  vimgolf [help]                # display this help and exit\n'
        '  vimgolf config [API_KEY]      # configure your vimgolf.com credentials\n'
        '  vimgolf local INFILE OUTFILE  # launch local challenge\n'
        '  vimgolf put CHALLENGE_ID      # launch vimgolf.com challenge\n'
        '  vimgolf list [PAGE][:LIMIT]   # list vimgolf.com challenges\n'
        '  vimgolf show CHALLENGE_ID     # show vimgolf.com challenge\n'
        '  vimgolf version               # display the version number'
    )

    if command == 'help':
        write(help_message)
        status = Status.SUCCESS
    elif command == 'local':
        if len(argv) != 4:
            usage = 'Usage: "vimgolf local INFILE OUTFILE"'
            write(usage, stream=sys.stderr, color='red')
            status = Status.FAILURE
        else:
            status = local(argv[2], argv[3])
    elif command == 'put':
        if len(argv) != 3:
            usage = 'Usage: "vimgolf put CHALLENGE_ID"'
            write(usage, stream=sys.stderr, color='red')
            status = Status.FAILURE
        else:
            status = put(argv[2])
    elif command == 'list':
        if not len(argv) in (2, 3):
            usage = 'Usage: "vimgolf list [PAGE]"'
            write(usage, stream=sys.stderr, color='red')
            status = Status.FAILURE
        else:
            kwargs = {}
            page_and_limit = argv[2] if len(argv) == 3 else ''
            parts = page_and_limit.split(':')
            try:
                if len(parts) > 0 and parts[0]: kwargs['page'] = int(parts[0])
                if len(parts) > 1: kwargs['limit'] = int(parts[1])
            except Exception:
                pass
            status = list_(**kwargs)
    elif command == 'show':
        if len(argv) != 3:
            usage = 'Usage: "vimgolf show CHALLENGE_ID"'
            write(usage, stream=sys.stderr, color='red')
            status = Status.FAILURE
        else:
            status = show(argv[2])
    elif command == 'config':
        if not len(argv) in (2, 3):
            usage = 'Usage: "vimgolf config [API_KEY]"'
            write(usage, stream=sys.stderr, color='red')
            status = Status.FAILURE
        else:
            api_key = argv[2] if len(argv) == 3 else None
            status = config(api_key)
    elif command == 'version':
        write(__version__)
        status = Status.SUCCESS
    else:
        write('Unknown command: {}'.format(command), stream=sys.stderr, color='red')
        status = Status.FAILURE

    exit_code = EXIT_SUCCESS if status == Status.SUCCESS else EXIT_FAILURE
    logger.info('exit({})'.format(exit_code))

    return exit_code


if __name__ == '__main__':
    sys.exit(sys.exit(main(sys.argv)))
