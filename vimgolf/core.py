import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request

from vimgolf import (
    logger,
    Status,
    VIMGOLF_API_KEY_PATH,
    VIMGOLF_ID_LOOKUP_PATH,
    EXPANSION_PREFIX,
    GOLF_HOST,
    VIMGOLF_CHALLENGES_PATH,
)
from vimgolf.utils import (
    write,
    http_request,
)


def validate_challenge_id(challenge_id):
    return challenge_id is not None and re.match(r'[\w\d]{24}', challenge_id)


def show_challenge_id_error():
    write('Invalid challenge ID', stream=sys.stderr, color='red')
    write('Please check the ID on vimgolf.com', stream=sys.stderr, color='red')


def validate_api_key(api_key):
    return api_key is not None and re.match(r'[\w\d]{32}', api_key)


def get_api_key():
    if not os.path.exists(VIMGOLF_API_KEY_PATH):
        return None
    with open(VIMGOLF_API_KEY_PATH, 'r') as f:
        api_key = f.read()
        return api_key


def set_api_key(api_key):
    with open(VIMGOLF_API_KEY_PATH, 'w') as f:
        f.write(api_key)


def show_api_key_help():
    write('An API key can be obtained from vimgolf.com', color='yellow')
    write('Please run "vimgolf config API_KEY" to set your API key', color='yellow')


def show_api_key_error():
    write('Invalid API key', stream=sys.stderr, color='red')
    write('Please check your API key on vimgolf.com', stream=sys.stderr, color='red')


def get_id_lookup():
    id_lookup = {}
    if os.path.exists(VIMGOLF_ID_LOOKUP_PATH):
        with open(VIMGOLF_ID_LOOKUP_PATH, 'r') as f:
            id_lookup = json.load(f)
    return id_lookup


def set_id_lookup(id_lookup):
    with open(VIMGOLF_ID_LOOKUP_PATH, 'w') as f:
        json.dump(id_lookup, f, indent=2)


def expand_challenge_id(challenge_id):
    if challenge_id.startswith(EXPANSION_PREFIX):
        challenge_id = get_id_lookup().get(challenge_id[1:], challenge_id)
    return challenge_id


def get_challenge_url(challenge_id):
    return urllib.parse.urljoin(GOLF_HOST, '/challenges/{}'.format(challenge_id))


def get_stored_challenges():
    result = {}
    for d in os.listdir(VIMGOLF_CHALLENGES_PATH):
        full_path = os.path.join(VIMGOLF_CHALLENGES_PATH, d)
        if not os.path.isdir(full_path):
            continue
        result[d] = Challenge(d)
    return result


class Challenge:
    def __init__(
            self,
            id,
            in_text=None,
            out_text=None,
            in_extension=None,
            out_extension=None,
            compliant=None,
            api_key=None):
        self.in_text = in_text
        self.out_text = out_text
        self.in_extension = in_extension
        self.out_extension = out_extension
        self.id = id
        self.compliant = compliant
        self.api_key = api_key

    @property
    def dir(self):
        return os.path.join(VIMGOLF_CHALLENGES_PATH, self.id)

    @property
    def spec_path(self):
        return os.path.join(self.dir, 'spec.json')

    @property
    def in_path(self):
        return os.path.join(self.dir, 'in{}'.format(self.in_extension))

    @property
    def out_path(self):
        return os.path.join(self.dir, 'out{}'.format(self.out_extension))

    @property
    def answers_path(self):
        return os.path.join(self.dir, 'answers.jsonl')

    @property
    def metadata_path(self):
        return os.path.join(self.dir, 'metadata.json')

    def save(self, spec):
        self._ensure_dir()
        with open(self.in_path, 'w') as f:
            f.write(self.in_text)
        with open(self.out_path, 'w') as f:
            f.write(self.out_text)
        with open(self.spec_path, 'w') as f:
            json.dump(spec, f)

    def add_answer(self, keys, correct, score, uploaded):
        self._ensure_dir()
        with open(self.answers_path, 'a') as f:
            f.write('{}\n'.format(json.dumps({
                'keys': keys,
                'correct': correct,
                'score': score,
                'uploaded': uploaded,
                'timestamp': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
            })))

    @property
    def answers(self):
        if not os.path.exists(self.answers_path):
            return []
        result = []
        with open(self.answers_path) as f:
            for raw_answer in f:
                result.append(json.loads(raw_answer))
        return sorted(result, key=lambda a: a['timestamp'])

    @property
    def spec(self):
        if not os.path.exists(self.spec_path):
            return {}
        with open(self.spec_path) as f:
            return json.load(f)

    @property
    def metadata(self):
        if not os.path.exists(self.metadata_path):
            return {}
        with open(self.metadata_path) as f:
            return json.load(f)

    def update_metadata(self, name=None, description=None):
        self._ensure_dir()
        uploaded = 0
        correct = 0
        stub_score = 10 ** 10
        best_score = stub_score
        for answer in self.answers:
            if answer['uploaded']:
                uploaded += 1
            if answer['correct']:
                correct += 1
                best_score = min(best_score, answer['score'])
        current_metadata = self.metadata
        current_metadata.update({
            'id': self.id,
            'url': get_challenge_url(self.id),
            'uploaded': uploaded,
            'correct': correct,
            'best_score': best_score if best_score != stub_score else -1,
        })
        if name:
            current_metadata['name'] = name
        if description:
            current_metadata['description'] = description
        with open(self.metadata_path, 'w') as f:
            json.dump(current_metadata, f)

    def _ensure_dir(self):
        if not os.path.exists(self.dir):
            os.makedirs(self.dir, exist_ok=True)


def upload_result(challenge_id, api_key, raw_keys):
    logger.info('upload_result(...)')
    status = Status.FAILURE
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
            status = Status.SUCCESS
    except Exception:
        logger.exception('upload failed')
    return status
