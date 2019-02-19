"""Maps keys recorded by vim to a printable representation"""

# This file has to be updated when vim changes internal representation.
# E.g., https://github.com/igrigorik/vimgolf/pull/188

# There are possibly ways to query vim to convert internal keycode
# representations to a human-readable format.
# E.g., https://github.com/vim/vim/issues/1810


def to_bytes(x):
    return x.to_bytes(2, 'big')


# Vim records key presses using 1) a single byte or 2) a 0x80 byte
# followed by two bytes. Parse the single-bytes and double-bytes.
# For the returned list, all values, including the single-bytes, are
# represented with two bytes.
def parse_keycodes(raw_keys):
    """
    Parse list of parsed keypress bytes from raw keypress
    representation saved by vim's -w.
    """
    keycodes = []
    tmp = list(reversed(raw_keys))
    while tmp:
        b0 = tmp.pop()
        if b0 == 0x80:
            b1 = tmp.pop()
            b2 = tmp.pop()
            keycode = bytes((b1, b2))
        else:
            keycode = to_bytes(b0)
        keycodes.append(keycode)
    return keycodes


# keystrokes that should not impact score (e.g., window focus)
IGNORED_KEYSTROKES = {
    b'\xfd\x35', # KE_IGNORE
    b'\xfd\x5e', # 7.2 compat "(I think?)"
    b'\xfd\x60', # 7.2 Focus Gained compat
    b'\xfd\x61', # Focus Gained (GVIM) (>7.4.1433)
    b'\xfd\x62', # Focus Gained (GVIM)
    b'\xfd\x63', # Focus Lost (GVIM)
}

_KEYCODE_REPR_LOOKUP = {}
# Control characters
for x in range(32):
    _KEYCODE_REPR_LOOKUP[to_bytes(x)] = '<C-{}>'.format(chr(x + 64))
# Printable characters
for x in range(32, 127):
    _KEYCODE_REPR_LOOKUP[to_bytes(x)] = chr(x)
# Single byte fallback
for x in range(127, 256):
    _KEYCODE_REPR_LOOKUP[to_bytes(x)] = '<0x{:02x}>'.format(x)
# Specially named control characters and others
_KEYCODE_REPR_LOOKUP[to_bytes(9)] = '<Tab>'
_KEYCODE_REPR_LOOKUP[to_bytes(10)] = '<NL>'
_KEYCODE_REPR_LOOKUP[to_bytes(13)] = '<CR>'
_KEYCODE_REPR_LOOKUP[to_bytes(27)] = '<Esc>'
_KEYCODE_REPR_LOOKUP[to_bytes(127)] = '<Del>'

# Double byte keys are from vimgolf's keylog.rb.
# Their source was:
#   1) :h terminal-options
#      (in particular, see :h terminal-key-codes)
#   2) vim sources: keymap.h, and misc2.c
_KEYCODE_REPR_LOOKUP.update({
    b'k1': '<F1>',
    b'k2': '<F2>',
    b'k3': '<F3>',
    b'k4': '<F4>',
    b'k5': '<F5>',
    b'k6': '<F6>',
    b'k7': '<F7>',
    b'k8': '<F8>',
    b'k9': '<F9>',
    b'k;': '<F10>',
    b'F1': '<F11>',
    b'F2': '<F12>',
    b'F3': '<F13>',
    b'F4': '<F14>',
    b'F5': '<F15>',
    b'F6': '<F16>',
    b'F7': '<F17>',
    b'F8': '<F18>',
    b'F9': '<F19>',
})

_KEYCODE_REPR_LOOKUP.update({
    b'%1': '<Help>',
    b'&8': '<Undo>',
    b'#2': '<S-Home>',
    b'*7': '<S-End>',
    b'K1': '<kHome>',
    b'K4': '<kEnd>',
    b'K3': '<kPageUp>',
    b'K5': '<kPageDown>',
    b'K6': '<kPlus>',
    b'K7': '<kMinus>',
    b'K8': '<kDivide>',
    b'K9': '<kMultiply>',
    b'KA': '<kEnter>',
    b'KB': '<kPoint>',
    b'KC': '<k0>',
    b'KD': '<k1>',
    b'KE': '<k2>',
    b'KF': '<k3>',
    b'KG': '<k4>',
    b'KH': '<k5>',
    b'KI': '<k6>',
    b'KJ': '<k7>',
    b'KK': '<k8>',
    b'KL': '<k9>',
})

_KEYCODE_REPR_LOOKUP.update({
    b'kP': '<PageUp>',
    b'kN': '<PageDown>',
    b'kh': '<Home>',
    b'@7': '<End>',
    b'kI': '<Insert>',
    b'kD': '<Del>',
    b'kb': '<BS>',
})

_KEYCODE_REPR_LOOKUP.update({
    b'ku': '<Up>',
    b'kd': '<Down>',
    b'kl': '<Left>',
    b'kr': '<Right>',
    b'#4': '<S-Left>',
    b'%i': '<S-Right>',
})

_KEYCODE_REPR_LOOKUP.update({
    b'kB': '<S-Tab>',
    b'\xffX': '<C-@>',
})

_KEYCODE_REPR_LOOKUP.update({
    b'\xfeX': '<0x80>',  # This is how you escape literal 0x80
})

# "These rarely-used modifiers should be combined with the next
#  stroke (like <S-Space>), but let's put them here for now"
_KEYCODE_REPR_LOOKUP.update({
    b'\xfc\x02': '<S->',
    b'\xfc\x04': '<C->',
    b'\xfc\x06': '<C-S->',
    b'\xfc\x08': '<A->',
    b'\xfc\x0a': '<A-S->',
    b'\xfc\x0c': '<C-A>',
    b'\xfc\x0e': '<C-A-S->',
    b'\xfc\x10': '<M->',
    b'\xfc\x12': '<M-S->',
    b'\xfc\x14': '<M-C->',
    b'\xfc\x16': '<M-C-S->',
    b'\xfc\x18': '<M-A->',
    b'\xfc\x1a': '<M-A-S->',
    b'\xfc\x1c': '<M-C-A>',
    b'\xfc\x1e': '<M-C-A-S->',
})

# KS_EXTRA keycodes (starting with 0x80 0xfd) are defined by an enum in
# Vim's keymap.h.
# Changes to vim source code require changes here.
_KEYCODE_REPR_LOOKUP.update({
    b'\xfd\x04': '<S-Up>',
    b'\xfd\x05': '<S-Down>',
    b'\xfd\x06': '<S-F1>',
    b'\xfd\x07': '<S-F2>',
    b'\xfd\x08': '<S-F3>',
    b'\xfd\x09': '<S-F4>',
    b'\xfd\x0a': '<S-F5>',
    b'\xfd\x0b': '<S-F6>',
    b'\xfd\x0c': '<S-F7>',
    b'\xfd\x0d': '<S-F9>',
    b'\xfd\x0e': '<S-F10>',
    b'\xfd\x0f': '<S-F10>',
    b'\xfd\x10': '<S-F11>',
    b'\xfd\x11': '<S-F12>',
    b'\xfd\x12': '<S-F13>',
    b'\xfd\x13': '<S-F14>',
    b'\xfd\x14': '<S-F15>',
    b'\xfd\x15': '<S-F16>',
    b'\xfd\x16': '<S-F17>',
    b'\xfd\x17': '<S-F18>',
    b'\xfd\x18': '<S-F19>',
    b'\xfd\x19': '<S-F20>',
    b'\xfd\x1a': '<S-F21>',
    b'\xfd\x1b': '<S-F22>',
    b'\xfd\x1c': '<S-F23>',
    b'\xfd\x1d': '<S-F24>',
    b'\xfd\x1e': '<S-F25>',
    b'\xfd\x1f': '<S-F26>',
    b'\xfd\x20': '<S-F27>',
    b'\xfd\x21': '<S-F28>',
    b'\xfd\x22': '<S-F29>',
    b'\xfd\x23': '<S-F30>',
    b'\xfd\x24': '<S-F31>',
    b'\xfd\x25': '<S-F32>',
    b'\xfd\x26': '<S-F33>',
    b'\xfd\x27': '<S-F34>',
    b'\xfd\x28': '<S-F35>',
    b'\xfd\x29': '<S-F36>',
    b'\xfd\x2a': '<S-F37>',
    b'\xfd\x2b': '<Mouse>',
    b'\xfd\x2c': '<LeftMouse>',
    b'\xfd\x2d': '<LeftDrag>',
    b'\xfd\x2e': '<LeftRelease>',
    b'\xfd\x2f': '<MiddleMouse>',
    b'\xfd\x30': '<MiddleDrag>',
    b'\xfd\x31': '<MiddleRelease>',
    b'\xfd\x32': '<RightMouse>',
    b'\xfd\x33': '<RightDrag>',
    b'\xfd\x34': '<RightRelease>',
    b'\xfd\x35': '<KE_IGNORE>',
    b'\xfd\x36': '<KE_TAB>',
    b'\xfd\x37': '<KE_S_TAB_OLD>',
})

# Vim 7.4.1433 removed KE_SNIFF. This is adjusted for in get_keycode_repr.
# TODO: adjust keycodes in the dictionary to reflect this removal.
_KEYCODE_REPR_LOOKUP.update({
    b'\xfd\x38': '<KE_SNIFF>',
    b'\xfd\x39': '<KE_XF1>',
    b'\xfd\x3a': '<KE_XF2>',
    b'\xfd\x3b': '<KE_XF3>',
    b'\xfd\x3c': '<KE_XF4>',
    b'\xfd\x3d': '<KE_XEND>',
    b'\xfd\x3e': '<KE_ZEND>',
    b'\xfd\x3f': '<KE_XHOME>',
    b'\xfd\x40': '<KE_ZHOME>',
    b'\xfd\x41': '<KE_XUP>',
    b'\xfd\x42': '<KE_XDOWN>',
    b'\xfd\x43': '<KE_XLEFT>',
    b'\xfd\x44': '<KE_XRIGHT>',
    b'\xfd\x45': '<KE_LEFTMOUSE_NM>',
    b'\xfd\x46': '<KE_LEFTRELEASE_NM>',
    b'\xfd\x47': '<KE_S_XF1>',
    b'\xfd\x48': '<KE_S_XF2>',
    b'\xfd\x49': '<KE_S_XF3>',
    b'\xfd\x4a': '<KE_S_XF4>',
    b'\xfd\x4b': '<ScrollWheelUp>',
    b'\xfd\x4c': '<ScrollWheelDown>',
})

# Horizontal scroll wheel support was added in Vim 7.3c.
_KEYCODE_REPR_LOOKUP.update({
    b'\xfd\x4d': '<ScrollWheelRight>',
    b'\xfd\x4e': '<ScrollWheelLeft>',
    b'\xfd\x4f': '<kInsert>',
    b'\xfd\x50': '<kDel>',
    b'\xfd\x51': '<0x9b>',        # :help <CSI>
    b'\xfd\x52': '<KE_SNR>',
    # b'\xfd\x53': '<KE_PLUG>',   # never used
    b'\xfd\x53': '<C-Left>',      # 7.2 compat
    # b'\xfd\x54': '<KE_CMDWIN>', # never used
    b'\xfd\x54': '<C-Right>',     # 7.2 compat
    b'\xfd\x55': '<C-Left>',      # 7.2 <C-Home> conflict
    b'\xfd\x56': '<C-Right>',     # 7.2 <C-End> conflict
    b'\xfd\x57': '<C-Home>',
    b'\xfd\x58': '<C-End>',
    b'\xfd\x59': '<KE_X1MOUSE>',
    b'\xfd\x5a': '<KE_X1DRAG>',
    b'\xfd\x5b': '<KE_X1RELEASE>',
    b'\xfd\x5c': '<KE_X2MOUSE>',
    b'\xfd\x5d': '<KE_X2DRAG>',
    # b'\xfd\x5e': '<KE_X2RELEASE>',
    b'\xfd\x5e': '<fd-5e>',       # 7.2 compat (I think?)
    b'\xfd\x5f': '<KE_DROP>',
    b'\xfd\x60': '<KE_CURSORHOLD>',
})

# gvim window focus changes are recorded as keystrokes
_KEYCODE_REPR_LOOKUP.update({
    b'\xfd\x60': '<FocusGained>',  # 7.2 Focus Gained compat
    b'\xfd\x61': '<FocusGained>',  # Focus Gained (GVIM) (>7.4.1433)
    b'\xfd\x62': '<FocusGained>',  # Focus Gained (GVIM)
    b'\xfd\x63': '<FocusLost>',    # Focus Lost (GVIM)
})


def get_keycode_repr(keycode):
    if keycode in _KEYCODE_REPR_LOOKUP:
        key = _KEYCODE_REPR_LOOKUP[keycode]
    else:
        key = ''.join('\\x{:02x}'.format(x) for x in keycode)
        key = '<' + key + '>'
    return key
