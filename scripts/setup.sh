#!/usr/bin/env bash

pip install -r requirements-dev.txt
pre-commit install
pre-commit install-hooks
pip install --editable . --config-settings editable_mode=strict
