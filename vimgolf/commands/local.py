import os
import tempfile

from vimgolf import logger
from vimgolf.challenge import Challenge
from vimgolf.play import play
from vimgolf.utils import format_


def local(infile, outfile):
    logger.info('local(%s, %s)', infile, outfile)
    with open(infile, 'r') as f:
        in_text = format_(f.read())
    with open(outfile, 'r') as f:
        out_text = format_(f.read())
    _, in_extension = os.path.splitext(infile)
    _, out_extension = os.path.splitext(outfile)
    challenge = Challenge(
        in_text=in_text,
        out_text=out_text,
        in_extension=in_extension,
        out_extension=out_extension,
        id=None,
    )
    with tempfile.TemporaryDirectory() as d:
        play(challenge, d)
