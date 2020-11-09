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

"""
yaml_to_junit-xml <path_to_latest_output_in_artifacts_folder> <path_to_artifacts_folder>
Script file to convert yaml file to Junit-xml format

Stages:
1. Convert the generated yaml output file to the list of dictionaries
2. Create a test suite and add the test cases
3. Generate the xml output file

Example:
 python yaml_to_junit-xml.py "{bamboo.build.working.directory}/artifacts/Testbed-One-Cambrionix/latest"
                             "{bamboo.build.working.directory}/artifacts}"
"""

import yaml
import argparse


def escape_quotes(s):
    """Replaces " in the string with &quot;."""
    return s.replace('"', '&quot;')


def main():
    parser = _parse_args()
    args = parser.parse_args()
    stream = open('%s/test_summary.yaml' % (args.test_path), "r")
    docs = list(yaml.load_all(stream))
    summary = docs[-1]
    testtime = 0.0
    test_cases = []
    begin_time = 0
    end_time = 0
    for doc in docs[1:]:
        try:  # prevents crash if record does not have valid timestamps
            if "Record" not in doc["Type"]:
                continue
            if begin_time == 0:
                begin_time = int(doc["Begin Time"])
            end_time = int(doc["End Time"])
        except Exception:
            pass

    testtime = (end_time - begin_time) / 1000.0
    with open('%s/test_results.xml' % (args.bamboo_path), 'w') as f:
        f.write("<?xml version=\"1.0\" ?>\n")

        try:   # prevent crash if summery doesn't present due to test getting timed out or hung
            f.write("<testsuite errors=\"{}\" failures=\"{}\" tests=\"{}\" time=\"{}\">\n"
                    .format(summary["Error"], summary["Failed"], summary["Requested"], str(testtime)))
        except Exception:
            print("WARN: Results are either partial or not present ")
            f.write("<testsuite errors=\"{}\" failures=\"{}\" tests=\"{}\" time=\"{}\">\n"
                    .format("0", "0", "0", str(testtime)))

        for doc in docs[1:]:
            if "Record" not in doc["Type"]:
                continue
            try:  # if record does not have valid timestamps, set time to 0
                testtime = (int(doc["End Time"]) - int(doc["Begin Time"])) / 1000.0
            except Exception:
                testtime = 0
            if "PASS" in doc["Result"]:
                f.write("\t<testcase classname=\"{}\" name=\"{}\" time=\"{}\"/>\n".format(
                    doc["Test Class"], doc["Test Name"], testtime))
            else:
                f.write("\t<testcase classname=\"{}\" name=\"{}\" time=\"{}\">\n".format(
                    doc["Test Class"], doc["Test Name"], testtime))
                if "SKIP" in doc["Result"]:
                    f.write("\t\t<skipped message=\"{}\" type=\"skip\">\n"
                            .format(escape_quotes(doc["Details"])))
                    f.write("\t\t</skipped>\n")
                elif "FAIL" in doc["Result"]:
                    f.write("\t\t<failure message=\"{}\" type=\"fail\">\n"
                            .format(escape_quotes(doc["Details"].split(":")[0])))
                    f.write("<![CDATA[ {} ]]>\n".format(doc["Stacktrace"]))
                    f.write("\t\t</failure>\n")
                else:  # some error condition
                    f.write("\t\t<error message=\"{}\" type=\"error\">\n"
                            .format(escape_quotes(doc["Details"].split(":")[0])))
                    f.write("<![CDATA[ {} ]]>\n".format(doc["Stacktrace"]))
                    f.write("\t\t</error>\n")
                f.write("\t</testcase>\n")
        f.write("</testsuite>")


def _parse_args():
    """returns a parser for this file

    Returns:
       ArgumentParser Object: parser to use on args

    Expected format:
       python yaml_to_junit_xml.py <path_to_latest_output_in_artifacts_folder> <path_to_artifacts_folder>

    """
    # bamboo dependent folders
    parser = argparse.ArgumentParser(description='Pass the directory')
    parser.add_argument(
        'test_path',
        nargs='?',
        default='artifacts/test_*/*mobly_logs',
        help='Path of directory')
    parser.add_argument(
        'bamboo_path',
        nargs='?',
        default='artifacts',
        help='Path of bamboo directory')
    return parser


if __name__ == '__main__':
    main()
