import concurrent.futures
import json
import sys
import urllib.parse
from collections import namedtuple

from terminaltables import AsciiTable

from vimgolf import (
    logger,
    Status,
    GOLF_HOST,
    MAX_REQUEST_WORKERS,
    LEADER_LIMIT,
)
from vimgolf.core import (
    expand_challenge_id,
    validate_challenge_id,
    show_challenge_id_error,
    get_challenge_url,
    Challenge,
)
from vimgolf.html import (
    parse_html,
    get_element_by_id,
    get_elements_by_classname,
    get_elements_by_tagname,
    get_text,
)
from vimgolf.utils import http_request, join_lines, write, bool_to_mark


def show(challenge_id, tracked=False):
    challenge_id = expand_challenge_id(challenge_id)
    logger.info('show(%s)', challenge_id)
    try:
        if not validate_challenge_id(challenge_id):
            show_challenge_id_error()
            return Status.FAILURE
        api_url = urllib.parse.urljoin(GOLF_HOST, '/challenges/{}.json'.format(challenge_id))
        page_url = get_challenge_url(challenge_id)
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_REQUEST_WORKERS) as executor:
            results = executor.map(http_request, [api_url, page_url])
            api_response = next(results)
            page_response = next(results)
        challenge_spec = json.loads(api_response.body)
        start_file = challenge_spec['in']['data']
        if not start_file.endswith('\n'):
            start_file += '\n'
        end_file = challenge_spec['out']['data']
        if not end_file.endswith('\n'):
            end_file += '\n'
        nodes = parse_html(page_response.body)
        content_element = get_element_by_id(nodes, 'content')
        content_grid_7_element = get_elements_by_classname(content_element.children, 'grid_7')[0]
        name_h3 = get_elements_by_tagname(content_grid_7_element.children, 'h3')[0]
        name = join_lines(get_text([name_h3]).strip())
        description_p_element = get_elements_by_tagname(content_grid_7_element.children, 'p')[0]
        description = join_lines(get_text([description_p_element]).strip())
        content_grid_5_element = get_elements_by_classname(content_element.children, 'grid_5')[0]
        Leader = namedtuple('Leader', 'username score')
        leaders = []
        leaderboard_divs = get_elements_by_tagname(content_grid_5_element.children, 'div')
        for leaderboard_div in leaderboard_divs:
            user_h6 = get_elements_by_tagname(leaderboard_div.children, 'h6')[0]
            username_anchor = get_elements_by_tagname(user_h6.children, 'a')[1]
            username = get_text([username_anchor]).strip()
            if username.startswith('@'):
                username = username[1:]
            score_div = get_elements_by_tagname(leaderboard_div.children, 'div')[0]
            score = int(get_text([score_div]).strip())
            leader = Leader(username=username, score=score)
            leaders.append(leader)
        separator = '-' * 50
        write(separator)
        write('{} ('.format(name), end=None)
        write(challenge_id, color='yellow', end=None)
        write(')')
        write(separator)
        write(page_url)
        write(separator)
        write('Leaderboard', color='green')
        if leaders:
            for leader in leaders[:LEADER_LIMIT]:
                write('{} {}'.format(leader.username.ljust(15), leader.score))
            if len(leaders) > LEADER_LIMIT:
                write('...')
        else:
            write('no entries yet', color='yellow')
        write(separator)
        write(description)
        write(separator)
        write('Start File', color='green')
        write(start_file, end=None)
        write(separator)
        write('End File', color='green')
        write(end_file, end=None)
        write(separator)

        challenge = Challenge(challenge_id)
        challenge.update_metadata(name, description)

        if tracked:
            write('Stats', color='green')
            metadata = challenge.metadata
            write('Uploaded: {}'.format(metadata['uploaded']))
            write('Correct Solutions: {}'.format(metadata['correct']))
            write('Self Best Score: {}'.format(metadata['best_score']))
            answers = challenge.answers
            ignored_answer_suffix = 'ZQ'
            answer_rows = [['Keys', 'Correct', 'Submitted', 'Score', 'Timestamp']]
            for answer in answers:
                keys = ''.join(answer['keys'])
                if keys.endswith(ignored_answer_suffix):
                    continue
                answer_row = [
                    keys,
                    bool_to_mark(answer['correct']),
                    bool_to_mark(answer['uploaded']),
                    answer['score'],
                    answer['timestamp'],
                ]
                answer_rows.append(answer_row)
            if len(answer_rows) > 1:
                write(AsciiTable(answer_rows).table)

    except Exception:
        logger.exception('challenge retrieval failed')
        write('The challenge retrieval has failed', stream=sys.stderr, color='red')
        write('Please check the challenge ID on vimgolf.com', stream=sys.stderr, color='red')
        return Status.FAILURE

    return Status.SUCCESS
