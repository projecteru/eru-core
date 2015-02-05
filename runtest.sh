#!/bin/sh

cp test/settings.py.sample ./settings.py
python -m unittest discover test '*_t.py'
