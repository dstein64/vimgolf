import os
import subprocess
import sys

from vimgolf import GOLF_VIM, Failure, logger
from vimgolf.utils import find_executable, write, confirm


def vim(args, **run_kwargs):
    try:
        _vim(args, **run_kwargs)
    except Failure:
        raise
    except Exception:
        logger.exception('{} execution failed'.format(GOLF_VIM))
        write('The execution of {} has failed'.format(GOLF_VIM), stream=sys.stderr, color='red')
        raise Failure()


def _vim(args, **run_kwargs):
    vim_path = find_executable(GOLF_VIM)
    if not vim_path:
        write('Unable to find "{}"'.format(GOLF_VIM), color='red')
        write('Please update your PATH to include the directory with "{}"'.format(GOLF_VIM), color='red')
        raise Failure()
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
            raise Failure()

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
