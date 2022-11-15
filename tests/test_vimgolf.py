from contextlib import redirect_stdout
import io
from collections import namedtuple
import os
import sys
import unittest

from vimgolf.html import (
    get_element_by_id,
    get_elements_by_tagname,
    get_text,
    parse_html,
)
from vimgolf.keys import tokenize_keycode_reprs
from vimgolf.vimgolf import (
    Challenge,
    format_,
    get_api_key,
    GOLF_HOST,
    http_request,
    main,
    play,
    RUBY_CLIENT_VERSION_COMPLIANCE,
    set_api_key,
    Status,
)

# XXX: The current tests are limited, only checking that some commands can run
# without error. The output text of the commands is not checked. The main
# vimgolf command, 'put', is not tested.

class TestVimgolf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._saved_api_key = get_api_key()

    @classmethod
    def tearDownClass(cls):
        if cls._saved_api_key is not None:
            set_api_key(cls._saved_api_key)

    def test_help_command(self):
        self.assertEqual(main(['vimgolf', 'help']), 0)

    def test_version_command(self):
        self.assertEqual(main(['vimgolf', 'version']), 0)

    def test_config_command(self):
        # WARN: This modifies the existing key, which is restored by
        # tearDownClass().
        self.assertEqual(main(['vimgolf', 'config']), 0)
        # The following key is not valid, but it's of the correct form.
        key = '00000000000000000000000000000000'
        self.assertEqual(main(['vimgolf', 'config', key]), 0)
        self.assertEqual(main(['vimgolf', 'config']), 0)
        malformed_key = '0'
        self.assertNotEqual(main(['vimgolf', 'config', malformed_key]), 0)

    def test_list_command(self):
        self.assertEqual(main(['vimgolf', 'list']), 0)

    def test_show_command(self):
        # First 'list', so that a relative ID (e.g., +1) can be used.
        with io.StringIO() as string_io, redirect_stdout(string_io):
            self.assertEqual(main(['vimgolf', 'list', '11:50']), 0)
            entry_counts = [int(x.split()[-3]) for x in string_io.getvalue().split('\n') if x]
        # Use the challenge with fewest entries to avoid VimGolf Issue #306.
        #   https://github.com/igrigorik/vimgolf/issues/306
        entry = min((x, idx) for idx, x in enumerate(entry_counts))[1] + 1
        self.assertEqual(main(['vimgolf', 'show', '+{}'.format(entry)]), 0)
        # The following ID is for 'Pascal's Triangle'
        # http://www.vimgolf.com/challenges/5ca2bc786b547e000c77fd52
        self.assertEqual(main(['vimgolf', 'show', '5ca2bc786b547e000c77fd52']), 0)
        # A workaround was added to avoid VimGolf Issue #306. Test that 'show'
        # works for 'Simple, Practical, and Common', a challenge that has the
        # issue without the workaround.
        # http://www.vimgolf.com/challenges/55b18bbea9c2c30d04000001
        self.assertEqual(main(['vimgolf', 'show', '55b18bbea9c2c30d04000001']), 0)
        # A workaround was added to avoid a cp1252 encoding exception on Windows
        # GitHub Actions for the following challenge.
        self.assertEqual(main(['vimgolf', 'show', '4d1c7ee635b40650b8000203']), 0)

    def test_ruby_client_version(self):
        response = http_request(GOLF_HOST)
        nodes = parse_html(response.body)
        copy_element = get_element_by_id(nodes, 'copy')
        version_b_element = get_elements_by_tagname(copy_element.children, 'b')[0]
        version_a_element = get_elements_by_tagname(version_b_element.children, 'a')[0]
        version = get_text(version_a_element.children)
        self.assertEqual(version, RUBY_CLIENT_VERSION_COMPLIANCE)

    def test_play(self):
        PlaySpec = namedtuple('PlaySpec', 'in_text out_text init_keys correct')
        play_specs = [
            PlaySpec('hello world', 'world', 'dWZZ', True),
            PlaySpec('hello world', 'world', 'dWZQ', False),
            PlaySpec('', 'hello world', 'ihello world<esc>ZZ', True),
            PlaySpec('', 'hello world', 'ihello world<ESC>ZZ', True),
            PlaySpec('', 'hello\nworld', 'ihello<cr>world<esc>ZZ', True),
            PlaySpec('text', 'hello\nworld', 'ddihello<cr>world<esc>ZZ', True),
            PlaySpec('hello world', '\thello world', '>>ZZ', True),
            PlaySpec('\thello world', 'hello world', '<<ZZ', True),
            PlaySpec('\thello world', 'hello world', '<lt><ZZ', True),
            PlaySpec('hello world', 'hello', 'A<bs><bs><bs><bs><bs><bs><esc>ZZ', True),
            PlaySpec('hello world', 'hello', 'A<bs><bs><bs><bs><bs><esc>ZZ', False),
            PlaySpec('hello world', 'hllo world', '<space><Space>i<bs><Esc>XZZ', True),
            PlaySpec('hello world', 'hello\n\\|world', 'WXi<enter><bslash><BAR><Esc>ZZ', True),
        ]
        win_github_actions = sys.platform == 'win32' and 'GITHUB_ACTIONS' in os.environ
        if not win_github_actions:
            # The following test hangs under GitHub Actions on Windows (but not on a direct test on
            # a Windows machine). The issue does not occur without the backslash entry in init_keys.
            # A test above also uses backslash without issue. The problem may be related to using
            # a backslash prior to <esc>. Perhaps this relates to the note under ":help dos-backslash":
            # "But when a backslash occurs before a special character (space, comma, backslash, etc.),
            # Vim removes the backslash."
            play_specs.append(PlaySpec('', '"\\', 'i"\\<esc>ZZ', True))
        # The following test fails on Windows (only under GitHub Actions), without hanging. The
        # backslash does not show up as an executed key.
        # TODO: If/when this passes in that scenario, the preceding test should also get updated
        # handling.
        # > Here are your keystrokes: ia"bc<Esc>ZZ
        play_specs.append(PlaySpec('', 'a"b\\c', 'ia"b\\c<esc>ZZ', not win_github_actions))

        for play_spec in play_specs:
            challenge = Challenge(
                in_text=format_(play_spec.in_text),
                out_text=format_(play_spec.out_text),
                in_extension='.txt',
                out_extension='.txt',
                id=None,
                compliant=None,
                api_key=None,
                init_keys=play_spec.init_keys,
            )
            stdin = sys.stdin
            sys.stdin = io.StringIO('q' + os.linesep)  # Choice> q (for quitting vimgolf)
            results = []
            status = play(challenge, results)
            sys.stdin = stdin
            self.assertEqual(status, Status.SUCCESS)
            self.assertEqual(results[-1].correct, play_spec.correct)
            self.assertEqual(len(results), 1)
            expected_score = len(tokenize_keycode_reprs(play_spec.init_keys))
            if (win_github_actions
                    and not results[-1].correct
                    and '\\' in play_spec.init_keys):
                # Account for backslash getting dropped on GitHub Actions on Windows.
                expected_score -= play_spec.init_keys.count('\\')
            self.assertEqual(results[-1].score, expected_score)


if __name__ == '__main__':
    unittest.main()
