#!/usr/bin/env bash
set -euo pipefail

# change to script directory
cd $(dirname "$0")

# make sure virtual env is active unless specifically turned off
if [[ -z "${VIRTUAL_ENV:-}" && "${SKIP_VENV:-}" -ne "1" ]]; then
    source venv/bin/activate
fi

echo "Running stubtest on fanstatic"
stubtest fanstatic \
         --mypy-config-file pyproject.toml \
         --allowlist tests/stubtest/fanstatic_allowlist.txt \

# the pyramid stubs are incomplete so we ignore missing stub
echo "Running stubtest on pyramid"
stubtest pyramid \
         --mypy-config-file pyproject.toml \
         --allowlist tests/stubtest/pyramid_allowlist.txt \
         --ignore-missing-stub

echo "Running stubtest on wtforms"
stubtest wtforms \
         --mypy-config-file pyproject.toml \
         --allowlist tests/stubtest/wtforms_allowlist.txt
