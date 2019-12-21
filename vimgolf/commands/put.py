import json
import re
import sys
import tempfile
import urllib.parse

from vimgolf import (
    __version__,
    logger,
    Status,
    GOLF_HOST,
    RUBY_CLIENT_VERSION_COMPLIANCE,
)
from vimgolf.core import (
    expand_challenge_id,
    validate_challenge_id,
    show_challenge_id_error,
    get_api_key,
    validate_api_key,
    show_api_key_help,
    Challenge,
    play,
)
from vimgolf.utils import write, confirm, http_request, format_


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
        cached_challenge = Challenge(challenge_id)
        cached_spec = cached_challenge.spec
        if cached_spec:
            write('Using locally cached challenge {}'.format(challenge_id), color='yellow')
            challenge_spec = cached_spec
        else:
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
                from distutils.version import StrictVersion
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
        api_key=api_key
    )
    challenge.save(spec=challenge_spec)
    with tempfile.TemporaryDirectory() as d:
        status = play(challenge, d)
    challenge.update_metadata()

    return status
