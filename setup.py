"""Setup configuration for aiorinnai package."""
import io
import os

from setuptools import setup

# The text of the README file
here = os.path.abspath(os.path.dirname(__file__))
try:
    with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
        long_description = '\n' + f.read()
except FileNotFoundError:
    long_description = "Python interface for Rinnai Control-R API"

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
    python_requires=">=3.11",
    install_requires=[
        'aiohttp>=3.6.1',
        'pycognito>=2024.5.1,<2025',
        'boto3>=1.26.0',
        'botocore>=1.29.0',
        'attrs>=21.0.0',
    ],
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-asyncio>=0.21.0',
            'pytest-cov>=4.0.0',
            'aioresponses>=0.7.4',
            'mypy>=1.0.0',
        ],
    },
    keywords=['rinnai', 'home automation', 'water heater'],
    packages=['aiorinnai'],
    package_data={'aiorinnai': ['py.typed']},
    zip_safe=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Typing :: Typed",
    ],
)
