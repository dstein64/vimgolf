import functools
import sys

import click

from vimgolf import (
    commands,
    Failure,
    __version__,
)
from vimgolf.utils import write


@click.group()
def main():
    pass


argument = click.argument
option = click.option


def command(*cmd_args, **cmd_kwargs):
    def result(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                fn(*args, **kwargs)
            except Failure:
                sys.exit(1)
        return main.command(*cmd_args, **cmd_kwargs)(wrapper)
    return result


@command()
@argument('in_file')
@argument('out_file')
def local(in_file, out_file):
    """launch local challenge """
    commands.local(in_file, out_file)


@command()
@argument('challenge_id')
def put(challenge_id):
    """launch vimgolf.com challenge"""
    commands.put(challenge_id)


@command('list')
@argument('spec', default='')
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
    commands.list_(**kwargs)


@command()
@argument('challenge_id')
@option('-t', '--tracked', is_flag=True, help='Include tracked data')
def show(challenge_id, tracked):
    """show vimgolf.com challenge"""
    commands.show(challenge_id, tracked)


@command()
@argument('api_key', default='')
def config(api_key):
    """configure your vimgolf.com credentials"""
    commands.config(api_key or None)


@command()
def version():
    """display the version number"""
    write(__version__)


if __name__ == '__main__':
    main()
