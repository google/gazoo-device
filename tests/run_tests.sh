#!/bin/bash
# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# RUN TESTS
# Can run unittests or mobly tests.
# Automatically reports a coverage report per test
# Run combine_coverage.sh -p artifacts to combine reports

CUR_DIR=$(dirname $0)
CONVERTER="${CUR_DIR}/_convert_coverage_file.py"
COVERAGE_PATH="artifacts"
COVERAGE_THRESHOLD="90"
PYTHON_VERSION=python3
TARGET=${PWD}
VIRTUAL_ENV="test_env"
UNIT_TEST_DIR="unit_tests"

HELP_MENU="Test executor for unit and functional tests\n"
HELP_MENU+="usage: run_tests.sh -d TEST_DIRECTORY -f TEST_FILE [-t testbed_model] [other_test_args]\n"
HELP_MENU+="1. Sets up with directory's requirements.txt\n"
HELP_MENU+="2. Runs Test\n"
HELP_MENU+="3. Reports test coverage of gazoo_device in format compatible with report and git-diff\n"
HELP_MENU+="Ex: run_tests.sh (defaults to running the unit tests)\n"
HELP_MENU+="Ex: run_tests.sh -d functional_tests -f auxiliary_device_common_test_suite -t One-Cambrionix\n"
HELP_MENU+="options:\n"
HELP_MENU+="  -h, --help     Print help and exit\n"
HELP_MENU+="  -d, --test_dir  TEST_DIRECTORY  relative link to test directory\n"
HELP_MENU+="  -f, --test_file TEST_FILE test file name\n"
HELP_MENU+="  -t, --testbed_model MODEL_NAME\n"



EXTRA_ARGS=()
while [[ $# -gt 0 ]]
do
key="$1"

case $key in
    -h|--help)
        PRINT_HELP=1
        shift # past argument
        ;;
    -d|--test_dir)
        TEST_DIR="$2"
        shift
        shift
        ;;
    -f|--test_file)
        TEST_FILE_NAME="$2"
        shift
        shift
        ;;
    -*)
        EXTRA_ARGS="$EXTRA_ARGS $1"
        shift
        ;;
    *) # no more options
        EXTRA_ARGS="$EXTRA_ARGS $1"
        shift
        ;;
esac
done

if [[ -z $PRINT_HELP ]]; then
    PRINT_HELP=0;
fi
if [[ -z $TEST_DIR ]]; then
    TEST_DIR="$UNIT_TEST_DIR"
fi
if [[ -z $TEST_FILE_NAME ]]; then
    TEST_FILE_NAME="unit_test_suite"
fi

if [ $PRINT_HELP -eq 1 ]; then
    printf "$HELP_MENU"
    exit 0
fi

if [ ! -d ${FULL_TEST_DIR} ]; then
    echo "Directory ${TEST_DIR} does not exist inside ${CUR_DIR}"
    echo "Perhaps a bad relative link?"
    echo "Current Directories:"
    for i in $(ls -d ${FULL_TEST_DIR}/*/); do
        echo "  ${i#${FULL_TEST_DIR}/}";
    done
fi
FULL_TEST_DIR="${CUR_DIR}/${TEST_DIR}"
REQUIREMENTS_FILE=$FULL_TEST_DIR/requirements.txt
if [ ! -f $REQUIREMENTS_FILE ]; then
    echo "Directory $FULL_TEST_DIR is missing a requirements.txt"
    ls $FULL_TEST_DIR
    echo $REQUIREMENTS_FILE
    exit 1
fi

if [[ ${TEST_FILE_NAME} != *.py ]]; then
    TEST_FILE_NAME="${TEST_FILE_NAME}.py"
fi
TEST_FILE="${CUR_DIR}/${TEST_DIR}/${TEST_FILE_NAME}"

if [ ! -f $TEST_FILE ]; then
    echo "Unable to locate ${TEST_FILE_NAME} in ${TEST_DIR}"
    echo "Found the following python files inside the directory:"
    for i in $(ls $FULL_TEST_DIR/*.py); do
        echo "  ${i#$FULL_TEST_DIR/}";
    done
    exit 1
fi


if [[ -z $VIRTUAL_ENV ]]; then
    echo "Removing virtual environment $VIRTUAL_ENV"
    rm -r $VIRTUAL_ENV
fi

if [[ ! -z $VIRTUAL_ENV ]]; then
    virtualenv --python=$PYTHON_VERSION $VIRTUAL_ENV
fi

# Needed if the tests are Mobly tests
MOBLY_LOGPATH=artifacts
if [[ -z ${MOBLY_LOGPATH} ]]; then
  mkdir MOBLY_LOGPATH
fi
source $VIRTUAL_ENV/bin/activate
pip install 'setuptools>=18.5'
pip install -r $REQUIREMENTS_FILE
pip install -e $CUR_DIR/.. # install gazoo_device
pip install -e $CUR_DIR  # Install GDM functional tests package
pip install coverage
pip install diff-cover
if [[ -z ${TEST_FILE} ]]; then
    echo "Test file ${TEST_FILE} doesn't exist"
    exit 1
fi
if [[ ${TEST_FILE} == *regression_test_suite* ]]; then
    # Coverage in the run script
    python ${TEST_FILE} ${EXTRA_ARGS}
else
    coverage run --source=gazoo_device ${TEST_FILE} $EXTRA_ARGS
    if [ -f .coverage ]; then
        COVERAGE_NAME=${TEST_FILE_NAME////.}
        cp .coverage ${MOBLY_LOGPATH}/.coverage.${COVERAGE_NAME}
    fi
fi

mkdir -p "$TARGET"
COV_RPT="$TARGET/coverage_report.txt"
DIF_COV_RPT="$TARGET/coverage_report_diff.txt"

# generate reports
coverage report > $COV_RPT
coverage xml
diff-cover coverage.xml > $DIF_COV_RPT
coverage html

# clean up artifacts
rm coverage.xml
rm .coverage

deactivate

echo
echo "Git Diff Coverage:"
tail -4 $DIF_COV_RPT
echo "See ${DIF_COV_RPT} for further details"
echo "Pop up ${PWD}/htmlcov/index.html in your browser to see interactive coverage."
echo
echo "Expected coverage: ${COVERAGE_THRESHOLD}% or more."

RETURN_CODE="0"
DIFF_COVERAGE=$(grep -e "Coverage: .*%" $DIF_COV_RPT)

if [[ ! -z $DIFF_COVERAGE ]]; then
	DIFF_COVERAGE_VALUE=$(echo $DIFF_COVERAGE | awk '{print $2}' | sed 's/%//g')
	if [ $DIFF_COVERAGE_VALUE -lt $COVERAGE_THRESHOLD ]; then
        RETURN_CODE="-1"
    	echo "Coverage diff (${DIFF_COVERAGE_VALUE}%) is below the ${COVERAGE_THRESHOLD}% threshold."
	else
        echo "Coverage diff (${DIFF_COVERAGE_VALUE}%) is above or equal to the ${COVERAGE_THRESHOLD}% threshold."
    fi
else
    echo "No diff found in coverage report."
fi
echo

exit $RETURN_CODE
