import io
import os

from setuptools import setup

# The text of the README file
here = os.path.abspath(os.path.dirname(__file__))
try:
    with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
        long_description = '\n' + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION

setup(
    name="aiorinnai",
    version="0.4.0a2",
    description="Python interface for Rinnai Control-R API",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url="https://github.com/explosivo22/aiorinnai",
    author="Brad Barbour",
    author_email="explosivo22@protonmail.com",
    license='Apache Software License',
    install_requires=[ 'aiohttp>=3.6.1', 'pycognito==2024.5.1' ],
    keywords=[ 'rinnai', 'home automation', 'water heater' ],
    packages=[ 'aiorinnai' ],
    zip_safe=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
)
