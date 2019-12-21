from vimgolf import logger, Failure
from vimgolf.api_key import (
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
        raise Failure()
    if api_key:
        set_api_key(api_key)
    else:
        api_key = get_api_key()
        if api_key:
            write(api_key)
        else:
            show_api_key_help()
