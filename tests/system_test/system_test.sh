#!/usr/bin/env bash

echo "Preparing system test..."
WORK_DIR=$(mktemp --directory)
ROOT_DIR="$(git rev-parse --show-toplevel)"
TEST_DIR="${ROOT_DIR}/tests/suite"
cp "${TEST_DIR}"/* "${WORK_DIR}"
pushd "${WORK_DIR}" &> /dev/null || exit 1
VENV="${WORK_DIR}/venv"
python3 -m venv "${VENV}"
. "${VENV}/bin/activate"
"${VENV}/bin/python3" -m pip install --quiet --upgrade pip
"${VENV}/bin/python3" -m pip install --quiet --editable "${ROOT_DIR}" || exit 1

echo "Executing system test..."
pytest -p pytest-litter --basetemp=tmp --check-litter  || exit 1

popd &> /dev/null || exit 1

echo "System test passed!"
