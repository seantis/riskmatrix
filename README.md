RiskMatrix [![Tests](https://github.com/seantis/riskmatrix/actions/workflows/tests.yml/badge.svg) [![codecov](https://codecov.io/gh/seantis/riskmatrix/graph/badge.svg?token=DVCXQ0B2TP)](https://codecov.io/gh/seantis/riskmatrix) [![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
================

Getting Started
---------------

- Clone repository

    git clone git@github.com:seantis/riskmatrix.git

- Change directory into your newly created project if not already there. Your
  current directory should be the same as this README.txt file and setup.py.

    cd riskmatrix

- Create a Python virtual environment, if not already created.

    python3 -m venv venv

- Then you want to activate it.

    source venv/bin/activate

- Upgrade packaging tools, if necessary.

    python -m pip install -U pip setuptools

- Install the project in editable mode with its testing requirements.

    pip install -r requirements.txt -r test_requirements.txt

- Install pre-commit hooks

    pre-commit install

- Create config file

    cp development.ini.example development.ini

- Initialize the database by adding a user.

    add_user development.ini

- Run your project's tests.

    pytest

- Run your project.

    pserve development.ini

- Login at http://localhost:6543 with your user's credentials
