vimgolf
=======

This project contains a [vimgolf](https://www.vimgolf.com/) client written in Python.

The user interface is similar to the [official vimgolf client](https://github.com/igrigorik/vimgolf),
with a few additions inspired by [vimgolf-finder](https://github.com/kciter/vimgolf-finder).

Installation
------------

#### Requirements

- Python 3.5 or greater

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
  vimgolf local INFILE OUTFILE  # launch local challenge
  vimgolf put CHALLENGE_ID      # launch vimgolf.com challenge
  vimgolf list [PAGE][:LIMIT]   # list vimgolf.com challenges
  vimgolf show CHALLENGE_ID     # show vimgolf.com challenge
  vimgolf version               # display the version number
```

`CHALLENGE_ID` can be a 24-character ID from vimgolf.com, or a plus-prefixed ID corresponding to the
last invocation of `vimgolf list`. For example, a `CHALLENGE_ID` of `+6` would correspond to the
sixth challenge presented in the most recent call to `vimgolf list`.

Demo
----

<img src="https://github.com/dstein64/vimgolf/blob/master/screencast.gif?raw=true" width="800"/>

License
-------

The source code has an [MIT License](https://en.wikipedia.org/wiki/MIT_License).

See [LICENSE](https://github.com/dstein64/vimgolf/blob/master/LICENSE).
