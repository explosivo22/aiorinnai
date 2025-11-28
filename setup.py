"""Shim for legacy tools that require setup.py.

All configuration is in pyproject.toml. This file exists for backward
compatibility with tools that don't yet support PEP 517/518.
"""
from setuptools import setup

setup()
