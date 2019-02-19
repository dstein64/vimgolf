"""Maps keys recorded by vim to a printable representation"""

# This file has to be updated when vim changes internal representation.
# E.g., https://github.com/igrigorik/vimgolf/pull/188

# There are possibly ways to query vim to convert internal keycode
# representations to a human-readable format.
# E.g., https://github.com/vim/vim/issues/1810

# Vim records key presses using 1) a single byte or 2) a 0x80 byte
# followed by two bytes. Parse the single-bytes and double-bytes.
def parse_keycodes(raw_keys):
    """
    Parse list of parsed keypress byte strings from raw keypress
    representation saved by vim's -w.
    """
    keycodes = []
    tmp = list(reversed(raw_keys))
    while tmp:
        b0 = tmp.pop()
        if b0 == 0x80:
            b1 = tmp.pop()
            b2 = tmp.pop()
            keycode = chr(b1) + chr(b2)
        else:
            keycode = chr(b0)
        keycodes.append(keycode)
    return keycodes

# keystrokes that should not impact score (e.g., window focus)
IGNORED_KEYSTROKES = {
    '\xfd\x35', # KE_IGNORE
    '\xfd\x5e', # 7.2 compat "(I think?)"
    '\xfd\x60', # 7.2 Focus Gained compat
    '\xfd\x61', # Focus Gained (GVIM) (>7.4.1433)
    '\xfd\x62', # Focus Gained (GVIM)
    '\xfd\x63', # Focus Lost (GVIM)
}

_KEYCODE_REPR_LOOKUP = {}
# Control characters
for x in range(32):
    _KEYCODE_REPR_LOOKUP[chr(x)] = '<C-{}>'.format(chr(x + 64))
# Printable characters
for x in range(32, 127):
    _KEYCODE_REPR_LOOKUP[chr(x)] = chr(x)
# Single byte fallback
for x in range(127, 256):
    _KEYCODE_REPR_LOOKUP[chr(x)] = '<0x{:02x}>'.format(x)
# Specially named control characters and others
_KEYCODE_REPR_LOOKUP[chr(9)] = '<Tab>'
_KEYCODE_REPR_LOOKUP[chr(10)] = '<NL>'
_KEYCODE_REPR_LOOKUP[chr(13)] = '<CR>'
_KEYCODE_REPR_LOOKUP[chr(27)] = '<Esc>'
_KEYCODE_REPR_LOOKUP[chr(127)] = '<Del>'

# Double byte keys are from vimgolf's keylog.rb.
# Their source was:
#   1) :h terminal-options
#      (in particular, see :h terminal-key-codes)
#   2) vim sources: keymap.h, and misc2.c
_KEYCODE_REPR_LOOKUP.update({
    'k1': '<F1>',
    'k2': '<F2>',
    'k3': '<F3>',
    'k4': '<F4>',
    'k5': '<F5>',
    'k6': '<F6>',
    'k7': '<F7>',
    'k8': '<F8>',
    'k9': '<F9>',
    'k;': '<F10>',
    'F1': '<F11>',
    'F2': '<F12>',
    'F3': '<F13>',
    'F4': '<F14>',
    'F5': '<F15>',
    'F6': '<F16>',
    'F7': '<F17>',
    'F8': '<F18>',
    'F9': '<F19>',
})

_KEYCODE_REPR_LOOKUP.update({
    '%1': '<Help>',
    '&8': '<Undo>',
    '#2': '<S-Home>',
    '*7': '<S-End>',
    'K1': '<kHome>',
    'K4': '<kEnd>',
    'K3': '<kPageUp>',
    'K5': '<kPageDown>',
    'K6': '<kPlus>',
    'K7': '<kMinus>',
    'K8': '<kDivide>',
    'K9': '<kMultiply>',
    'KA': '<kEnter>',
    'KB': '<kPoint>',
    'KC': '<k0>',
    'KD': '<k1>',
    'KE': '<k2>',
    'KF': '<k3>',
    'KG': '<k4>',
    'KH': '<k5>',
    'KI': '<k6>',
    'KJ': '<k7>',
    'KK': '<k8>',
    'KL': '<k9>',
})

_KEYCODE_REPR_LOOKUP.update({
    'kP': '<PageUp>',
    'kN': '<PageDown>',
    'kh': '<Home>',
    '@7': '<End>',
    'kI': '<Insert>',
    'kD': '<Del>',
    'kb': '<BS>',
})

_KEYCODE_REPR_LOOKUP.update({
    'ku': '<Up>',
    'kd': '<Down>',
    'kl': '<Left>',
    'kr': '<Right>',
    '#4': '<S-Left>',
    '%i': '<S-Right>',
})

_KEYCODE_REPR_LOOKUP.update({
    'kB': '<S-Tab>',
    '\xffX': '<C-@>',
})

_KEYCODE_REPR_LOOKUP.update({
    '\xfeX': '<0x80>',  # This is how you escape literal 0x80
})

# "These rarely-used modifiers should be combined with the next
#  stroke (like <S-Space>), but let's put them here for now"
_KEYCODE_REPR_LOOKUP.update({
    '\xfc\x02': '<S->',
    '\xfc\x04': '<C->',
    '\xfc\x06': '<C-S->',
    '\xfc\x08': '<A->',
    '\xfc\x0a': '<A-S->',
    '\xfc\x0c': '<C-A>',
    '\xfc\x0e': '<C-A-S->',
    '\xfc\x10': '<M->',
    '\xfc\x12': '<M-S->',
    '\xfc\x14': '<M-C->',
    '\xfc\x16': '<M-C-S->',
    '\xfc\x18': '<M-A->',
    '\xfc\x1a': '<M-A-S->',
    '\xfc\x1c': '<M-C-A>',
    '\xfc\x1e': '<M-C-A-S->',
})

# KS_EXTRA keycodes (starting with 0x80 0xfd) are defined by an enum in
# Vim's keymap.h.
# Changes to vim source code require changes here.
_KEYCODE_REPR_LOOKUP.update({
    '\xfd\x04': '<S-Up>',
    '\xfd\x05': '<S-Down>',
    '\xfd\x06': '<S-F1>',
    '\xfd\x07': '<S-F2>',
    '\xfd\x08': '<S-F3>',
    '\xfd\x09': '<S-F4>',
    '\xfd\x0a': '<S-F5>',
    '\xfd\x0b': '<S-F6>',
    '\xfd\x0c': '<S-F7>',
    '\xfd\x0d': '<S-F9>',
    '\xfd\x0e': '<S-F10>',
    '\xfd\x0f': '<S-F10>',
    '\xfd\x10': '<S-F11>',
    '\xfd\x11': '<S-F12>',
    '\xfd\x12': '<S-F13>',
    '\xfd\x13': '<S-F14>',
    '\xfd\x14': '<S-F15>',
    '\xfd\x15': '<S-F16>',
    '\xfd\x16': '<S-F17>',
    '\xfd\x17': '<S-F18>',
    '\xfd\x18': '<S-F19>',
    '\xfd\x19': '<S-F20>',
    '\xfd\x1a': '<S-F21>',
    '\xfd\x1b': '<S-F22>',
    '\xfd\x1c': '<S-F23>',
    '\xfd\x1d': '<S-F24>',
    '\xfd\x1e': '<S-F25>',
    '\xfd\x1f': '<S-F26>',
    '\xfd\x20': '<S-F27>',
    '\xfd\x21': '<S-F28>',
    '\xfd\x22': '<S-F29>',
    '\xfd\x23': '<S-F30>',
    '\xfd\x24': '<S-F31>',
    '\xfd\x25': '<S-F32>',
    '\xfd\x26': '<S-F33>',
    '\xfd\x27': '<S-F34>',
    '\xfd\x28': '<S-F35>',
    '\xfd\x29': '<S-F36>',
    '\xfd\x2a': '<S-F37>',
    '\xfd\x2b': '<Mouse>',
    '\xfd\x2c': '<LeftMouse>',
    '\xfd\x2d': '<LeftDrag>',
    '\xfd\x2e': '<LeftRelease>',
    '\xfd\x2f': '<MiddleMouse>',
    '\xfd\x30': '<MiddleDrag>',
    '\xfd\x31': '<MiddleRelease>',
    '\xfd\x32': '<RightMouse>',
    '\xfd\x33': '<RightDrag>',
    '\xfd\x34': '<RightRelease>',
    '\xfd\x35': '<KE_IGNORE>',
    '\xfd\x36': '<KE_TAB>',
    '\xfd\x37': '<KE_S_TAB_OLD>',
})

# Vim 7.4.1433 removed KE_SNIFF. This is adjusted for in get_keycode_repr.
# TODO: adjust keycodes in the dictionary to reflect this removal.
_KEYCODE_REPR_LOOKUP.update({
    '\xfd\x38': '<KE_SNIFF>',
    '\xfd\x39': '<KE_XF1>',
    '\xfd\x3a': '<KE_XF2>',
    '\xfd\x3b': '<KE_XF3>',
    '\xfd\x3c': '<KE_XF4>',
    '\xfd\x3d': '<KE_XEND>',
    '\xfd\x3e': '<KE_ZEND>',
    '\xfd\x3f': '<KE_XHOME>',
    '\xfd\x40': '<KE_ZHOME>',
    '\xfd\x41': '<KE_XUP>',
    '\xfd\x42': '<KE_XDOWN>',
    '\xfd\x43': '<KE_XLEFT>',
    '\xfd\x44': '<KE_XRIGHT>',
    '\xfd\x45': '<KE_LEFTMOUSE_NM>',
    '\xfd\x46': '<KE_LEFTRELEASE_NM>',
    '\xfd\x47': '<KE_S_XF1>',
    '\xfd\x48': '<KE_S_XF2>',
    '\xfd\x49': '<KE_S_XF3>',
    '\xfd\x4a': '<KE_S_XF4>',
    '\xfd\x4b': '<ScrollWheelUp>',
    '\xfd\x4c': '<ScrollWheelDown>',
})

# Horizontal scroll wheel support was added in Vim 7.3c.
_KEYCODE_REPR_LOOKUP.update({
    '\xfd\x4d': '<ScrollWheelRight>',
    '\xfd\x4e': '<ScrollWheelLeft>',
    '\xfd\x4f': '<kInsert>',
    '\xfd\x50': '<kDel>',
    '\xfd\x51': '<0x9b>',        # :help <CSI>
    '\xfd\x52': '<KE_SNR>',
    # '\xfd\x53': '<KE_PLUG>',   # never used
    '\xfd\x53': '<C-Left>',      # 7.2 compat
    # '\xfd\x54': '<KE_CMDWIN>', # never used
    '\xfd\x54': '<C-Right>',     # 7.2 compat
    '\xfd\x55': '<C-Left>',      # 7.2 <C-Home> conflict
    '\xfd\x56': '<C-Right>',     # 7.2 <C-End> conflict
    '\xfd\x57': '<C-Home>',
    '\xfd\x58': '<C-End>',
    '\xfd\x59': '<KE_X1MOUSE>',
    '\xfd\x5a': '<KE_X1DRAG>',
    '\xfd\x5b': '<KE_X1RELEASE>',
    '\xfd\x5c': '<KE_X2MOUSE>',
    '\xfd\x5d': '<KE_X2DRAG>',
    # '\xfd\x5e': '<KE_X2RELEASE>',
    '\xfd\x5e': '<fd-5e>',       # 7.2 compat (I think?)
    '\xfd\x5f': '<KE_DROP>',
    '\xfd\x60': '<KE_CURSORHOLD>',
})

# gvim window focus changes are recorded as keystrokes
_KEYCODE_REPR_LOOKUP.update({
    '\xfd\x60': '<FocusGained>',  # 7.2 Focus Gained compat
    '\xfd\x61': '<FocusGained>',  # Focus Gained (GVIM) (>7.4.1433)
    '\xfd\x62': '<FocusGained>',  # Focus Gained (GVIM)
    '\xfd\x63': '<FocusLost>',    # Focus Lost (GVIM)
})


def get_keycode_repr(keycode):
    if keycode in _KEYCODE_REPR_LOOKUP:
        key = _KEYCODE_REPR_LOOKUP[keycode]
    else:
        key = '-'.join('{:02x}'.format(ord(x)) for x in keycode)
        key = '<' + key + '>'
    return key
