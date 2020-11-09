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

r"""Generates a behavior dictionary from an GDM device log.


python generate_behavior_dict -d device_log.txt --include_logs --starting_line_timestamp "<2019-04-01 14:03:12.380534>" --ending_line_timestamp "<2019-04-01 14:03:12.479514>"


    Ex:
    <2019-04-02 13:02:19.338209> GDM-M: Note: opened transport for port 1 in 0.0202209949493s
    <2019-04-02 13:02:19.338426> GDM-M: Note: expecting any patterns from ['ember> '] using response lines and 2000 search window in 30.0s
    <2019-04-02 13:02:19.443638> GDM-1: ember> [NO EOL]
    <2019-04-02 13:02:19.452650> GDM-M: Note: found pattern 'ember> ' at index 0
    <2019-04-02 13:02:19.452899> GDM-M: Note: mode any expect completed with u'' remaining patterns in 0.114032030106s
    <2019-04-02 13:02:19.706319> GDM-M: Note: expecting any patterns from ['^>'] using response lines and 2000 search window in 15.0s
    <2019-04-02 13:02:19.707106> GDM-M: Note: wrote command '\n' to port 0
    <2019-04-02 13:02:19.776002> GDM-0:
    <2019-04-02 13:02:19.776466> GDM-0:
    <2019-04-02 13:02:19.776812> GDM-0: >
    <2019-04-02 13:02:19.821724> GDM-M: Note: found pattern '^>' at index 0
    <2019-04-02 13:02:19.821874> GDM-M: Note: mode any expect completed with u'' remaining patterns in 0.114416837692s
    <2019-04-02 13:02:19.825245> GDM-M: Note: expecting any patterns from ['ACK \\w+: (.+$)', 'Bootloader'] using response lines and 2000 search window in 15.0s
    <2019-04-02 13:02:19.825827> GDM-M: Note: wrote command 'vnfo\n' to port 0
    <2019-04-02 13:02:19.913443> GDM-0: >
    <2019-04-02 13:02:19.913986> GDM-0: > vnfo
    <2019-04-02 13:02:19.914329> GDM-0: Handling command: vnfo
    <2019-04-02 13:02:19.915045> GDM-0: ACK vnfo: __EM358_APP__=1.2d22, __LOCKFW__=2.0.62, __VOICEFW__=1.2.12, __VOICEENGLISH__=1.2.6, __VOICESPANISH__=1.2.6, __VOICEFRENCH__=1.2.6, __VOICETONE__=1.2.8,
    <2019-04-02 13:02:19.915452> GDM-0:
    <2019-04-02 13:02:19.941088> GDM-M: Note: found pattern 'ACK \\w+: (.+$)' at index 0
    <2019-04-02 13:02:19.941267> GDM-M: Note: mode any expect completed with u'Bootloader' remaining patterns in 0.11440205574s


    Returns:
        self.fake_responder.behavior_dict = {
            "\n": " \n\n> \n",
            "vnfo\n": "> \n> vnfo\nHandling command: vnfo\nACK vnfo: __EM358_APP__=1.2d22, __LOCKFW__=2.0.62, __VOICEFW__=1.2.12, __VOICEENGLISH__=1.2.6, __VOICESPANISH__=1.2.6, __VOICEFRENCH__=1.2.6, __VOICETONE__=1.2.8, \n\n",
        }
        self.fake_responder.response= "\nember> [NO EOL]\n"

    Note: If there are multiple responses to the same command: they will be returned as such:
       "sysenv\n": ["aloha\n", "[123.34] something\naloha\n"],

    User has the option of condensing these to a single string:
       "sysenv\n": "aloha\n"

    Or treating it as a iterator:
        "sysenv\n": iter(["aloha\n", "[123.34] something\naloha\n"]),

    For super long lines, the user can either remove lines or convert to more manageable entry:
       "vnfo\n": ("> \n> vnfo\nHandling command: vnfo\nACK vnfo: __EM358_APP__=1.2d22, "
                  "__LOCKFW__=2.0.62, __VOICEFW__=1.2.12, __VOICEENGLISH__=1.2.6, __VOICESPANISH__=1.2.6,"
                  " __VOICEFRENCH__=1.2.6, __VOICETONE__=1.2.8, \n\n"),


    Rules of behavior_dict:
      "GDM-M: Note wrote command '<command>'" is a command.
      "GDM-M: Note expecting .." is the start of expected response
      "GDM-M : * expect completed or "GDM-M: expect timed out" is the end of an expected response
      "GDM-0: NLCLIENT@@", " GDM-0: SYSLOG--@@"  annotate log lines.
      All other lines are considered response lines.

    This runs through each line, classifying it as an annotation (GDM-M) or actual device line (GDM-0 and GDM-1)
    It joins together all the lines that are a response to a particular command.
"""
from __future__ import print_function
import argparse
import json
import re
import sys

VERBOSE = False
LOGLINE_MATCHES = ["NLCLIENT@@", "SYSLOG--@@"]
COMMAND_REGEX = 'Note: wrote command u?["\'](.*)["\'] to port'
BUTTON_PRESS_REGEX = r"(click|press) button (\w+)"
EXPECT_START = "GDM-M: Note: expecting"
EXPECT_END_REGEX = "expect (completed|timed)"
RESPONSE_EXPECT = "response lines"
GDM_ANNOTATION = "GDM-M"


def dprint(msg):
    if VERBOSE:
        print(msg)


def get_lines(device_log_file, starting_line_timestamp=None, ending_line_timestamp=None):
    with open(device_log_file, 'r') as a_file:
        lines = a_file.readlines()

    if starting_line_timestamp:
        starting_index_list = [index for index, line in enumerate(lines)
                               if line.startswith(starting_line_timestamp)]
        if not starting_index_list:
            raise ValueError(
                "No line starts with starting_timestamp {} in {}".format(
                    starting_line_timestamp, device_log_file))
        lines = lines[starting_index_list[0]:]

    if ending_line_timestamp:
        ending_index_list = [index for index, line in enumerate(
            lines) if line.startswith(ending_line_timestamp)]
        if not ending_index_list:
            raise ValueError(
                "No line starts with ending_timestamp {} in {}".format(
                    ending_line_timestamp, device_log_file))
        lines = lines[:ending_index_list[0]]
    return lines


def remove_timestamps(lines):
    return [line[line.index('>') + 2:] for line in lines]


def process_cmd_lines(lines):
    """Receives lines and returns a behavior dict."""
    behavior_dict = {}
    response = ""
    current_cmd = ""
    current_entry = []
    include_logs = True
    for line in lines:
        if line.startswith(GDM_ANNOTATION):  # informational
            dprint("Annotation: {!r}".format(line))
            if re.search(COMMAND_REGEX, line):  # Command

                match = re.search(COMMAND_REGEX, line)
                current_cmd = match.group(1)
                dprint("\tSetting new cmd: {!r}".format(current_cmd))
                if "\\n" in current_cmd:
                    current_cmd = current_cmd.replace("\\n", "\n").replace("\\\n", "\\n")

            elif re.search(BUTTON_PRESS_REGEX, line):
                match = re.search(BUTTON_PRESS_REGEX, line)
                current_cmd = str(match.group(2))
                dprint("\tSetting new cmd: {!r}".format(current_cmd))

            elif line.startswith(EXPECT_START):  # start expect
                if RESPONSE_EXPECT in line:
                    include_logs = False
                else:
                    include_logs = True
                if "" not in behavior_dict:  # add any lines gathered to response
                    behavior_dict[""] = [current_entry]
                else:
                    behavior_dict[""].append(current_entry)
                current_entry = []
                dprint("\tStarting expect with include logs {}".format(include_logs))
            elif re.search(EXPECT_END_REGEX, line):  # end of expect
                dprint("\tStopping expect")
                entry = "".join(current_entry)
                dprint("\tAdding {!r} with entry {!r}".format(current_cmd, entry))
                if current_cmd not in behavior_dict:
                    behavior_dict[current_cmd] = [entry]
                else:
                    behavior_dict[current_cmd].append(entry)
                current_cmd = ""
                current_entry = []
        else:  # device output
            if any(prefix in line for prefix in LOGLINE_MATCHES):
                if include_logs:
                    line = line[7:]  # remove 'GDM-0: '
                    dprint("Add loglines entry {}".format(line))
                    current_entry.append(line)
            else:
                # Ensure commands can be handled by fake_responder easily
                if "GDMHELLO" in line:
                    line = re.sub(r'CMD-(\d+)', 'CMD-0001', line[7:])
                else:
                    line = re.sub(r'CMD-(\d+)', 'CMD-0002', line[7:])
                dprint("Add entry {}".format(line))
                current_entry.append(line)

    for cmd, entries in behavior_dict.iteritems():
        if all(entry == entries[0] for entry in entries):
            behavior_dict[cmd] = entries[0]  # replace list with string as all are the same

    if "" in behavior_dict:
        response = behavior_dict[""]
        del behavior_dict[""]
    return behavior_dict, response


def main(device_log_file, starting_line_timestamp,
         ending_line_timestamp, include_response):
    lines = get_lines(device_log_file, starting_line_timestamp, ending_line_timestamp)
    lines = remove_timestamps(lines)
    behavior_dict, response = process_cmd_lines(lines)
    print(behavior_dict.keys())

    print("")
    print("")
    print("self.fake_responder.behavior_dict =",)
    print(json.dumps(behavior_dict, indent=4))
    if include_response:
        print("self.fake_responder.response=",)
        print(json.dumps(response, indent=4))

if __name__ == '__main__':
    args = sys.argv[1:]
    parser = argparse.ArgumentParser(description='behavior dict generator')
    parser.add_argument(
        '-i',
        '--include_response',
        dest='include_response',
        action='store_true',
        default=False,
        help='Include response (can be quite long)')
    parser.add_argument(
        '-k',
        '--known_log_line_prefix',
        dest='log_line_prefix',
        default=None,
        help='Use "GDM-1" for adb and ssh devices')
    parser.add_argument(
        '-s',
        '--starting_line_timestamp',
        dest='starting_line_timestamp',
        default=None,
        help='Log line Timestamp in logfile at which to start creating behavior_dict')
    parser.add_argument(
        '-v',
        '--verbose',
        dest='verbose',
        action='store_true',
        default=False,
        help='Verbose for debugging purposes')
    parser.add_argument(
        '-e',
        '--ending_line_timestamp',
        dest='ending_line_timestamp',
        default=None,
        help='Log line Timestamp in logfile at which to end creating behavior_dict')
    parser.add_argument(
        '-d',
        '--device_log_file',
        dest='device_log_file',
        required=True,
        help='File to use to create behavior dict')
    args = parser.parse_args(args)
    if args.verbose:
        VERBOSE = True
    if args.log_line_prefix:
        LOGLINE_MATCHES.append(args.log_line_prefix)

    main(
        args.device_log_file,
        args.starting_line_timestamp,
        args.ending_line_timestamp,
        args.include_response)
