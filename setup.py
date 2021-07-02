import os.path
from setuptools import setup

# The text of the README file
with open(os.path.join(HERE, "README.md")) as fid:
    README = fid.read()

setuptools.setup(
    name="api-rinnaicontrolr",
    version="0.2.1.a1",
    description="Python interface for Rinnai Control-R API",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/explosivo22/rinnaicontrolr",
    author="Brad Barbour",
    author_email="barbourbj@gmail.com",
    license='Apache Software License',
    install_requires=[ 'aiohttp>=3.7.0' ],
    keywords=[ 'rinnai', 'home automation', 'water heater' ],
    packages=[ 'rinnaicontrolr' ],
    zip_safe=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
)
