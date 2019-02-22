from cgi import parse_header
from collections import namedtuple
import filecmp
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

from vimgolf.html_utils import (
    get_elements_by_classname,
    get_element_by_id,
    get_elements_by_tagname,
    parse_html,
    TextNode
)
from vimgolf.keys import IGNORED_KEYSTROKES, get_keycode_repr, parse_keycodes


version_txt = os.path.join(os.path.dirname(__file__), 'version.txt')
with open(version_txt, 'r') as f:
    __version__ = f.read().strip()

STATUS_SUCCESS = 0
STATUS_FAILURE = 1


# ************************************************************
# * Configuration and Global Variables
# ************************************************************

GOLF_HOST = os.environ.get('GOLF_HOST', 'https://www.vimgolf.com')
GOLF_DIFF = os.environ.get('GOLF_DIFF', 'vim -d -n')
GOLF_VIM = os.environ.get('GOLF_VIM', 'vim')

USER_AGENT = 'vimgolf'

RUBY_CLIENT_VERSION_COMPLIANCE = '0.4.8'

CONFIG_HOME = os.environ.get('XDG_CONFIG_HOME', os.path.join(os.path.expanduser('~'), '.config'))
VIMGOLF_CONFIG_PATH = os.path.join(CONFIG_HOME, 'vimgolf')
os.makedirs(VIMGOLF_CONFIG_PATH, exist_ok=True)
VIMGOLF_API_KEY_FILENAME = 'api_key'


# ************************************************************
# * Utils
# ************************************************************

HttpResponse = namedtuple('HttpResponse', 'code msg headers body')


def http_get(url):
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    response = urllib.request.urlopen(request)
    try:
        # TODO: get rid of cgi dependency. do this manually
        charset = parse_header(response.getheader('Content-Type'))[1]['charset']
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
        'red':    '\033[31m',
        'green':  '\033[32m',
        'orange': '\033[33m',
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


def format_(string):
    """dos2unix and add newline to end."""
    string = string.replace('\r\n', '\n').replace('\r', '\n')
    if not string.endswith('\n'):
        string = string + '\n'
    return string


# ************************************************************
# * Core
# ************************************************************

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
    write('An API key can be obtained from vimgolf.com', color='orange')
    write('Please run "vimgolf config API_KEY" to set your API key', color='orange')


Challenge = namedtuple('Challenge', 'in_text out_text in_ext out_ext id compliant api_key')


def play(challenge, workspace):
    infile = os.path.join(workspace, 'in')
    if challenge.in_ext:
        infile += challenge.in_ext
    outfile = os.path.join(workspace, 'out')
    if challenge.out_ext:
        outfile += challenge.out_ext
    logfile = os.path.join(workspace, 'log')
    with open(outfile, 'w') as f:
        f.write(challenge.out_text)

    # TODO: here is where the loop should start.
    #       so that infile is clobbered. logfile is automatically clobbered from -W.
    #       outfile doesn't change...

    with open(infile, 'w') as f:
        f.write(challenge.in_text)

    args = GOLF_VIM.split()
    vimrc = os.path.join(os.path.dirname(__file__), 'vimgolf.vimrc')
    args += [
        '-Z',          # restricted mode, utilities not allowed
        '-n',          # no swap file, memory only editing
        '--noplugin',  # no plugins
        '--nofork',    # so gvim doesn't return immediately
        '-i', 'NONE',  # don't load .viminfo (e.g., has saved macros, etc.)
        '+0',          # start on line 0
        '-u', vimrc,   # vimgolf .vimrc
        '-U', 'NONE',  # don't load .gvimrc
        '-W', logfile, # keylog file (overwrites existing)
        infile
    ]
    subprocess.run(args)

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
        color = 'orange' if len(keycode_repr) > 1 else None
        write(keycode_repr, color=color, end=None)
    write('')

    if correct:
        write('Success! Your output matches.', color='green')
        write('Your score:', color='green')
    else:
        write('Uh oh, looks like your entry does not match the desired output.', color='red')
        write('Your score for this failed attempt:', color='red')
    write(score)

    if challenge.id and challenge.compliant and challenge.api_key:
        # TODO: this scenario means uploads are eligible
        pass

    return STATUS_SUCCESS


def local(infile, outfile):
    with open(infile, 'r') as f:
        in_text = format_(f.read())
    with open(outfile, 'r') as f:
        out_text = format_(f.read())
    _, in_ext = os.path.splitext(infile)
    _, out_ext = os.path.splitext(outfile)
    challenge = Challenge(
        in_text=in_text,
        out_text=out_text,
        in_ext=in_ext,
        out_ext=out_ext,
        id=None,
        compliant=None,
        api_key=None)
    with tempfile.TemporaryDirectory() as d:
        status = play(challenge, d)
    return status


def put(challenge_id):
    api_key = get_api_key()
    if api_key is None:
        show_api_key_help()
        # TODO: change this exit to a question of whether to proceed, without upload
        # capability. Or "press any key to continue without upload capability".
        # In either case, be sure to set a flag that uploads disabled.
        exit(1)

    # TODO: create copy of infile so it's not destructively modified
    # TODO: check if credentials are set, and if not, issue a warning...

    url = urllib.parse.urljoin(GOLF_HOST, 'challenges/{}.json'.format(challenge_id))
    try:
        response = http_get(url)
    except  Exception:
        # TODO: error message
        return STATUS_FAILURE
    challenge_spec = json.loads(response.body)
    compliant = True
    if challenge_spec['client'] != RUBY_CLIENT_VERSION_COMPLIANCE:
        compliant = False
        # TODO: Issue warning and make sure not to upload.
        # TODO: Also check for fields appropriately... (in/out)
        # TODO: Also use Python versioning library for checking if client version is older or newer...
        # TODO: Also check that 'client' exists. If it doesn't, then not compliant. May also want to check
        #       for response type json.
        pass

    # TODO: create temporary infile/outfile from challenge_spec. replace \r\n with \n.
    #       sanitize file extension and retain in new filename.
    #       make sure file ends with \n
    infile = None
    outfile = None

    # TODO: play() should take strings as input and construct
    #       temporary files...
    challenge = Challenge(infile=infile, outfile=outfile, id=challenge_id, compliant=compliant)
    status = play(challenge)

    return status


def list_(page=None, limit=10):
    Listing = namedtuple('Listing', 'id name n_entries')
    try:
        listings = []
        url = GOLF_HOST
        if page is not None:
            url = urllib.parse.urljoin(GOLF_HOST, '/?page={}'.format(page))
        response = http_get(url)
        nodes = parse_html(response.body)
        challenge_elements = get_elements_by_classname(nodes, 'challenge')
        for element in challenge_elements:
            id_, name, n_entries = None, None, None
            anchor = get_elements_by_tagname(element.children, 'a')[0]
            href = anchor.get_attr('href')
            id_ = href.split('/')[-1]
            name = anchor.children[0].data
            for child in element.children:
                if isinstance(child, TextNode) and 'entries' in child.data:
                    n_entries = int([x for x in child.data.split() if x.isdigit()][0])
                    break
            listing = Listing(id=id_, name=name, n_entries=n_entries)
            listings.append(listing)
    except Exception:
        # TODO: error message
        return STATUS_FAILURE

    for idx, listing in enumerate(listings):
        if idx >= limit: break
        write('{}. '.format(idx + 1), end=None)
        write('{} - {} entries ('.format(listing.name, listing.n_entries), end=None)
        write(listing.id, color='orange', end=None)
        write(')')

    # TODO: retain the mapping of listing number to ID, so it can be used by put and show
    # (probably prepended by : when used)

    return STATUS_SUCCESS


def show(challenge_id):
    try:
        api_url = urllib.parse.urljoin(GOLF_HOST, 'challenges/{}.json'.format(challenge_id))
        api_response = http_get(api_url)
        challenge_spec = json.loads(api_response.body)
        start_file = challenge_spec['in']['data']
        if not start_file.endswith('\n'):
            start_file += '\n'
        end_file = challenge_spec['out']['data']
        if not end_file.endswith('\n'):
            end_file += '\n'
        page_url = urllib.parse.urljoin(GOLF_HOST, 'challenges/{}'.format(challenge_id))
        page_response = http_get(page_url)
        nodes = parse_html(page_response.body)
        content_element = get_element_by_id(nodes, 'content')
        grid_7_element = get_elements_by_classname(content_element.children, 'grid_7')[0]
        h3_element = get_elements_by_tagname(grid_7_element.children, 'h3')[0]
        name = join_lines(h3_element.children[0].children[0].data)
        p_element = get_elements_by_tagname(grid_7_element.children, 'p')[0]
        description = join_lines(p_element.children[0].data)
    except Exception:
        # TODO: error message
        return STATUS_FAILURE

    separator = '-' * 50
    write(separator)
    write('{} ('.format(name), end=None)
    write(challenge_id, color='orange', end=None)
    write(')')
    write(separator)
    write(description)
    write(separator)
    write('Start File', color='green')
    write(start_file, end=None)
    write(separator)
    write('End File', color='green')
    write(end_file, end=None)
    write(separator)

    return STATUS_SUCCESS


def config(api_key=None):
    if api_key is not None and not re.match('[\w\d]{32}', api_key):
        message = 'Invalid key, please check your key on vimgolf.com'
        write(message, stream=sys.stderr, color='red')
        return STATUS_FAILURE

    if api_key:
        set_api_key(api_key)
        return STATUS_SUCCESS

    api_key = get_api_key()
    if api_key:
        write(api_key)
    else:
        show_api_key_help()

    return STATUS_SUCCESS


# ************************************************************
# * Command Line Interface
# ************************************************************

def main(argv=sys.argv):
    if len(argv) < 2:
        command = 'help'
    else:
        command = argv[1]

    help_message = (
        'Commands:\n'
        '  vimgolf [help]                # display this help and exit\n'
        '  vimgolf config [API_KEY]      # configure your VimGolf credentials\n'
        '  vimgolf local INFILE OUTFILE  # launch local challenge\n'
        '  vimgolf put CHALLENGE_ID      # launch vimgolf.com challenge\n'
        '  vimgolf list [PAGE][:LIMIT]   # list vimgolf.com challenges\n'
        '  vimgolf show CHALLENGE_ID     # show vimgolf.com challenge\n'
        '  vimgolf version               # display the version number'
    )

    if command == 'help':
        write(help_message)
        status = STATUS_SUCCESS
    elif command == 'local':
        if len(argv) != 4:
            usage = 'Usage: "vimgolf local INFILE OUTFILE"'
            write(usage, stream=sys.stderr, color='red')
            status = STATUS_FAILURE
        else:
            status = local(argv[2], argv[3])
    elif command == 'put':
        if len(argv) != 3:
            usage = 'Usage: "vimgolf put CHALLENGE_ID"'
            write(usage, stream=sys.stderr, color='red')
            status = STATUS_FAILURE
        else:
            status = put(argv[2])
    elif command == 'list':
        if not len(argv) in (2, 3):
            usage = 'Usage: "vimgolf list [PAGE]"'
            write(usage, stream=sys.stderr, color='red')
            status = STATUS_FAILURE
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
            status = STATUS_FAILURE
        else:
            status = show(argv[2])
    elif command == 'config':
        if not len(argv) in (2, 3):
            usage = 'Usage: "vimgolf config [API_KEY]"'
            write(usage, stream=sys.stderr, color='red')
            status = STATUS_FAILURE
        else:
            api_key = argv[2] if len(argv) == 3 else None
            status = config(api_key)
    elif command == 'version':
        write(__version__)
        status = STATUS_SUCCESS
    else:
        write('Unknown command: {}'.format(command), stream=sys.stderr, color='red')
        status = STATUS_FAILURE

    return status


if __name__ == '__main__':
    sys.exit(sys.exit(main(sys.argv)))
