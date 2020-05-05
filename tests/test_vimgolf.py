import unittest

from vimgolf.vimgolf import (
    get_api_key,
    GOLF_HOST,
    http_request,
    main,
    RUBY_CLIENT_VERSION_COMPLIANCE,
    set_api_key,
)
from vimgolf.html import (
    get_element_by_id,
    get_elements_by_tagname,
    get_text,
    parse_html,
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
        self.assertEqual(main(['vimgolf', 'list']), 0)
        self.assertEqual(main(['vimgolf', 'show', '+1']), 0)
        # The following ID is for 'Simple, Practical, and Common'
        # http://www.vimgolf.com/challenges/55b18bbea9c2c30d04000001
        challenge_id = '55b18bbea9c2c30d04000001'
        self.assertEqual(main(['vimgolf', 'show', challenge_id]), 0)

    def test_ruby_client_version(self):
        response = http_request(GOLF_HOST)
        nodes = parse_html(response.body)
        copy_element = get_element_by_id(nodes, 'copy')
        version_b_element = get_elements_by_tagname(copy_element.children, 'b')[0]
        version_a_element = get_elements_by_tagname(version_b_element.children, 'a')[0]
        version = get_text(version_a_element.children)
        self.assertEqual(version, RUBY_CLIENT_VERSION_COMPLIANCE)


if __name__ == '__main__':
    unittest.main()
