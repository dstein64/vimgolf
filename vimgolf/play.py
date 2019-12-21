import filecmp
import json
import os
import sys
import urllib.parse

from vimgolf import logger, GOLF_VIM, PLAY_VIMRC_PATH, GOLF_HOST, Failure
from vimgolf.challenge import get_challenge_url
from vimgolf.keys import parse_keycodes, IGNORED_KEYSTROKES, get_keycode_repr
from vimgolf.utils import write, input_loop, http_request
from vimgolf.vim import vim


def play(challenge, workspace):
    logger.info('play(...)')

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

        vimrc = PLAY_VIMRC_PATH
        play_args = [
            '-Z',           # restricted mode, utilities not allowed
            '-n',           # no swap file, memory only editing
            '--noplugin',   # no plugins
            '-i', 'NONE',   # don't load .viminfo (e.g., has saved macros, etc.)
            '+0',           # start on line 0
            '-u', vimrc,    # vimgolf .vimrc
            '-U', 'NONE',   # don't load .gvimrc
            '-W', logfile,  # keylog file (overwrites existing)
            infile,
        ]
        try:
            vim(play_args, check=True)
        except Failure:
            raise
        except Exception:
            logger.exception('{} execution failed'.format(GOLF_VIM))
            write('The execution of {} has failed'.format(GOLF_VIM), stream=sys.stderr, color='red')
            raise Failure()

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

        uploaded = False
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
            for opt in menu:
                write('[{}] {}'.format(*opt), color='yellow')
            selection = input_loop('Choice> ')
            if selection not in valid_codes:
                write('Invalid selection: {}'.format(selection), stream=sys.stderr, color='red')
            elif selection == 'd':
                diff_args = ['-d', '-n', infile, outfile]
                vim(diff_args)
            elif selection == 'w':
                success = upload_result(challenge.id, challenge.api_key, raw_keys)
                if success:
                    write('Uploaded entry!', color='green')
                    leaderboard_url = get_challenge_url(challenge.id)
                    write('View the leaderboard: {}'.format(leaderboard_url), color='green')
                    uploaded = True
                    upload_eligible = False
                else:
                    write('The entry upload has failed', stream=sys.stderr, color='red')
                    message = 'Please check your API key on vimgolf.com'
                    write(message, stream=sys.stderr, color='red')
            else:
                break

        if challenge.id:
            challenge.add_answer(
                keys=keycode_reprs,
                score=score,
                correct=correct,
                uploaded=uploaded,
            )

        if selection == 'q':
            break
        write('Retrying vimgolf challenge', color='yellow')

    write('Thanks for playing!', color='green')


def upload_result(challenge_id, api_key, raw_keys):
    logger.info('upload_result(...)')
    success = False
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
            success = True
    except Exception:
        logger.exception('upload failed')
    return success
