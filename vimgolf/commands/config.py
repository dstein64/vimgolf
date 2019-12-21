from vimgolf import logger, Status
from vimgolf.core import (
    validate_api_key,
    show_api_key_error,
    set_api_key,
    get_api_key,
    show_api_key_help,
)
from vimgolf.utils import write


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
