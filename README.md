[![Build Status](https://github.com/dstein64/vimgolf/workflows/build/badge.svg)](https://github.com/dstein64/vimgolf/actions)

vimgolf
=======

This project contains a [vimgolf](https://www.vimgolf.com/) client written in Python.

The user interface is similar to the [official vimgolf client](https://github.com/igrigorik/vimgolf),
with a few additions inspired by [vimgolf-finder](https://github.com/kciter/vimgolf-finder), and an
optional way to specify keys to type when launching a challenge.

Installation
------------

#### Requirements

- Python 3.6 or greater

#### Install

```sh
$ pip3 install vimgolf
```

#### Update

```sh
$ pip3 install --upgrade vimgolf
```

Usage
-----

#### Launch

If the launcher script was installed within a directory on your `PATH`, vimgolf can be launched
directly.

```sh
$ vimgolf
```

Otherwise, vimgolf can be launched by passing its module name to Python.

```sh
$ python3 -m vimgolf
```

#### Commands

```text
  vimgolf [help]                # display this help and exit
  vimgolf config [API_KEY]      # configure your VimGolf credentials
  vimgolf local IN OUT [KEYS]   # launch local challenge
  vimgolf put CHALLENGE [KEYS]  # launch vimgolf.com challenge
  vimgolf list [PAGE][:LIMIT]   # list vimgolf.com challenges
  vimgolf show CHALLENGE        # show vimgolf.com challenge
  vimgolf diff CHALLENGE        # show diff for vimgolf.com challenge
  vimgolf version               # display the version number
```

`CHALLENGE` can be a 24-character ID from vimgolf.com, or a plus-prefixed ID corresponding to the
last invocation of `vimgolf list`. For example, a `CHALLENGE` of `+6` would correspond to the sixth
challenge presented in the most recent call to `vimgolf list`.

For the `local` command, `IN` and `OUT` are paths to files.

For the `local` and `put` commands, the optional `KEYS` specifies a set of keys to enter when
launching the challenge. For example, `ihello world<esc>` would enter insert mode, type "hello
world", and then switch back to normal mode. The character `<` is assumed to start a special
sequence (e.g., `<esc>`) if that would be possible given the characters that follow. The input
string should use `<lt>` to disambiguate.

<details open><summary><h2>Demo</h2></summary>

<img src="https://github.com/dstein64/media/blob/main/vimgolf/screencast.gif?raw=true" width="800"/>

</details>

License
-------

The source code has an [MIT License](https://en.wikipedia.org/wiki/MIT_License).

See [LICENSE](https://github.com/dstein64/vimgolf/blob/master/LICENSE).
