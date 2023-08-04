#!/usr/bin/env bash

echo "Preparing system test..."
WORK_DIR=$(mktemp --directory)
THIS_DIR="$(dirname "$0")"
TEST_DIR="${THIS_DIR}/../pytester"
cp "${TEST_DIR}/*" "${WORK_DIR}"
pushd "${WORK_DIR}" &> /dev/null || exit 1
VENV="${WORK_DIR}/venv"
python -m venv "${VENV}"
. "${VENV}/bin/activate"
"${VENV}/bin/python3" -m pip install --quiet --upgrade pip
"${VENV}/bin/python3" -m pip install --quiet --editable "$(git rev-parse --show-toplevel)" || exit 1

echo "Executing system test..."
pytest -p pytest-litter --basetemp=tmp  || exit 1

popd &> /dev/null || exit 1

echo "System test passed!"
