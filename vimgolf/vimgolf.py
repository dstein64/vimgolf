import filecmp
import os
import subprocess
import sys
import tempfile

from vimgolf.keys import IGNORED_KEYSTROKES, get_keycode_repr, parse_keycodes

version_txt = os.path.join(os.path.dirname(__file__), 'version.txt')
with open(version_txt, 'r') as f:
    __version__ = f.read().strip()

STATUS_SUCCESS = 0
STATUS_FAILURE = 1

GOLF_HOST = os.environ.get('GOLF_HOST', 'https://www.vimgolf.com')
GOLF_DIFF = os.environ.get('GOLF_DIFF', 'vim -d -n')
GOLF_VIM = os.environ.get('GOLF_VIM', 'vim')

HELP_MESSAGE = (
    'Commands:\n'
    '  vimgolf [help]                # display this help and exit\n'
    '  vimgolf local INFILE OUTFILE  # launch local challenge\n'
    '  vimgolf put CHALLENGE_ID      # launch vimgolf.com challenge\n'
    '  vimgolf setup [API_KEY]       # configure your VimGolf credentials\n'
    '  vimgolf version               # display the version number'
)


def write(string, end='\n', stream=None, color=None):
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


def play(infile, outfile):
    """Warning: Destructively modifies 'infile'"""
    with tempfile.NamedTemporaryFile(mode='w+b') as f:
        args = GOLF_VIM.split()
        vimrc = os.path.join(os.path.dirname(__file__), 'vimgolf.vimrc')
        logfile = f.name
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

    write('Score: {}'.format(score))
    write('Here are your keystrokes:', color='green')
    for keycode_repr in keycode_reprs:
        color = 'red' if len(keycode_repr) > 1 else None
        write(keycode_repr, color=color, end=None)
    write('')
    print(logfile)

    return STATUS_SUCCESS


def local(infile, outfile):
    # TODO: create copy of infile so it's not destructively modified
    status = play(infile, outfile)
    return status


def put(challenge_id):
    # TODO: create copy of infile so it's not destructively modified
    # TODO: check if credentials are set, and if not, issue a warning...
    return STATUS_SUCCESS


def setup(api_key=None):
    return STATUS_SUCCESS


def main(argv=sys.argv):
    if len(argv) < 2:
        command = 'help'
    else:
        command = argv[1]
    if command == 'help':
        write(HELP_MESSAGE)
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
    elif command == 'setup':
        if not len(argv) in (2, 3):
            usage = 'Usage: "vimgolf setup [API_KEY]"'
            write(usage, stream=sys.stderr, color='red')
            status = STATUS_FAILURE
        else:
            api_key = argv[2] if len(argv) == 2 else None
            status = setup(api_key)
    elif command == 'version':
        write(__version__)
        status = STATUS_SUCCESS
    else:
        write('Unknown command: {}'.format(command), stream=sys.stderr, color='red')
        status = STATUS_FAILURE
    return status


if __name__ == '__main__':
    sys.exit(sys.exit(main(sys.argv)))
