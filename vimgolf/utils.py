import os
import sys
import urllib.parse
import urllib.request
from collections import namedtuple
from pathlib import Path

USER_AGENT = 'vimgolf'

HttpResponse = namedtuple('HttpResponse', 'code msg headers body')


def http_request(url, data=None):
    request = urllib.request.Request(url, data, headers={'User-Agent': USER_AGENT})
    response = urllib.request.urlopen(request)
    try:
        charset = response.getheader('Content-Type').split(';')[1].split('=')[1].strip()
    except Exception:
        charset = 'utf-8'
    body = response.read().decode(charset)
    return HttpResponse(
        code=response.code,
        msg=response.msg,
        headers=response.getheaders(),
        body=body
    )


def join_lines(string):
    lines = [line.strip() for line in string.split('\n') if line]
    return ' '.join(lines)


def maybe_colorize(string, stream, color=None):
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
    if color and hasattr(stream, 'isatty') and stream.isatty():
        string = color_lookup[color] + string + end_color
    return string


def write(string, end='\n', stream=None, color=None):
    string = str(string)
    if stream is None:
        stream = sys.stdout
    string = maybe_colorize(string, stream, color)
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
            if required and not selection:
                continue
            return selection
        except EOFError:
            write('', stream=sys.stderr)
            sys.exit(1)
        except KeyboardInterrupt:
            write('', stream=sys.stderr)
            write('KeyboardInterrupt', stream=sys.stderr)
            continue


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
    def fixcase(path):
        return str(Path(path).resolve())
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


bool_to_mark = lambda m: '✅' if m else '❌'
