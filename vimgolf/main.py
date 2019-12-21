import functools
import sys

import click

from vimgolf import commands
from vimgolf import Status, EXIT_SUCCESS, EXIT_FAILURE, __version__
from vimgolf.utils import write


@click.group()
def main():
    pass


def exit_status(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        status = fn(*args, **kwargs)
        exit_code = EXIT_SUCCESS if status == Status.SUCCESS else EXIT_FAILURE
        sys.exit(exit_code)
    return wrapper


argument = click.argument
option = click.option
command = main.command


@command()
@argument('in_file')
@argument('out_file')
@exit_status
def local(in_file, out_file):
    """launch local challenge """
    return commands.local(in_file, out_file)


@command()
@argument('challenge_id')
@exit_status
def put(challenge_id):
    """launch vimgolf.com challenge"""
    return commands.put(challenge_id)


@command('list')
@argument('spec', default='')
@exit_status
def list_(spec):
    """list vimgolf.com challenges (spec syntax: [PAGE][:LIMIT])"""
    page_and_limit = spec
    kwargs = {}
    parts = page_and_limit.split(':')
    try:
        if len(parts) > 0 and parts[0]:
            kwargs['page'] = int(parts[0])
        if len(parts) > 1:
            kwargs['limit'] = int(parts[1])
    except Exception:
        pass
    return commands.list_(**kwargs)


@command()
@argument('challenge_id')
@option('-t', '--tracked', is_flag=True, help='Include tracked data')
@exit_status
def show(challenge_id, tracked):
    """show vimgolf.com challenge"""
    return commands.show(challenge_id, tracked)


@command()
@argument('api_key', default='')
@exit_status
def config(api_key):
    """configure your vimgolf.com credentials"""
    return commands.config(api_key or None)


@command('version')
def version_cmd():
    """display the version number"""
    write(__version__)


if __name__ == '__main__':
    main()
