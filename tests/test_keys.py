from vimgolf.keys import Keys


cases = [
    (b'\x5a\x5a', ['Z', 'Z']),
    (b'\x80\x6b\x31\x5a\x5a', ['<F1>', 'Z', 'Z']),
    (b'\x1b\x18\x0e\x0d', ['<Esc>', '<C-X>', '<C-N>', '<CR>']),
]


def test():
    for raw_keys, keycode_reprs in cases:
        keys_from_raw_keys = Keys.from_raw_keys(raw_keys)
        keys_from_keycode_reprs = Keys.from_keycode_reprs(keycode_reprs)
        for keys in [keys_from_raw_keys, keys_from_keycode_reprs]:
            assert keys.raw_keys == raw_keys
            assert keys.keycode_reprs == keycode_reprs
