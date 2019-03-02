import os
from setuptools import setup

version_txt = os.path.join(os.path.dirname(__file__), 'vimgolf', 'version.txt')
with open(version_txt, 'r') as f:
    version = f.read().strip()

setup(
    author='Daniel Steinberg',
    author_email='ds@dannyadam.com',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Unix',
        'Programming Language :: Python :: 3',
        'Topic :: Text Editors',
        'Topic :: Games/Entertainment',
    ],
    description='A vimgolf client written in Python',
    entry_points={
        'console_scripts': ['vimgolf=vimgolf.vimgolf:main'],
    },
    keywords=['vim', 'vimgolf'],
    license='MIT',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    name='vimgolf',
    package_data={'vimgolf': ['version.txt', 'vimgolf.vimrc']},
    packages=['vimgolf'],
    python_requires='>=3.5',
    url='https://github.com/dstein64/vimgolf',
    version=version,
)
