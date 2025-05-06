#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup
from codecs import open
from os import path
import re

dir_prefix = path.abspath(path.dirname(__file__))
module_keywords = {}

with open(path.join(dir_prefix, 'README.rst'), encoding='utf-8') as f:
    module_keywords['long_description'] = f.read()

setup(**module_keywords)
