# Copyright 2022 Google LLC
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

"""Fake event file content."""

SAMPLE_MESSAGE_EVENT = b"""{"sample.message": [], "sample.message2": [], "raw_log_line": "[APPL] Some unique message", "system_timestamp": "2020-09-23 16:40:18.650343", "matched_timestamp": "2020-09-23 16:40:18.650513"}
"""

SAMPLE_MESSAGE_EVENTS_SUBSET = b"""{"sample.message": [], "sample.message2": [], "raw_log_line": "[APPL] Some unique message", "system_timestamp": "2020-09-23 17:03:51.734849", "matched_timestamp": "2020-09-23 17:03:51.734904"}
{"sample.state": ["9"], "raw_log_line": "[APPL] Some other message with group data 9", "system_timestamp": "2020-09-23 17:03:51.734849", "matched_timestamp": "2020-09-23 17:03:51.734881"}
{"sample.message3": [], "raw_log_line": "[APPL] This is another message", "system_timestamp": "2020-09-23 17:03:51.734849", "matched_timestamp": "2020-09-23 17:03:51.734858"}
{"sample.message": [], "sample.message2": [], "raw_log_line": "[APPL] Some unique message", "system_timestamp": "2020-09-23 17:03:51.734775", "matched_timestamp": "2020-09-23 17:03:51.734832"}
{"sample.state": ["8"], "raw_log_line": "[APPL] Some other message with group data 8", "system_timestamp": "2020-09-23 17:03:51.734775", "matched_timestamp": "2020-09-23 17:03:51.734809"}
{"sample.message3": [], "raw_log_line": "[APPL] This is another message", "system_timestamp": "2020-09-23 17:03:51.734775", "matched_timestamp": "2020-09-23 17:03:51.734784"}
{"sample.message": [], "sample.message2": [], "raw_log_line": "[APPL] Some unique message", "system_timestamp": "2020-09-23 17:03:51.734609", "matched_timestamp": "2020-09-23 17:03:51.734754"}
{"sample.state": ["7"], "raw_log_line": "[APPL] Some other message with group data 7", "system_timestamp": "2020-09-23 17:03:51.734609", "matched_timestamp": "2020-09-23 17:03:51.734641"}
{"sample.message3": [], "raw_log_line": "[APPL] This is another message", "system_timestamp": "2020-09-23 17:03:51.734609", "matched_timestamp": "2020-09-23 17:03:51.734617"}
{"sample.message": [], "sample.message2": [], "raw_log_line": "[APPL] Some unique message", "system_timestamp": "2020-09-23 17:03:51.734536", "matched_timestamp": "2020-09-23 17:03:51.734591"}
"""

ALL_SAMPLE_MESSAGE_EVENTS = b"""{"sample.message": [], "sample.message2": [], "raw_log_line": "[APPL] Some unique message", "system_timestamp": "2020-09-23 04:01:09.539385", "matched_timestamp": "2020-09-23 04:01:09.539896"}
{"sample.message": [], "sample.message2": [], "raw_log_line": "[APPL] Some unique message", "system_timestamp": "2020-09-23 04:01:09.539923", "matched_timestamp": "2020-09-23 04:01:09.539986"}
{"sample.message": [], "sample.message2": [], "raw_log_line": "[APPL] Some unique message", "system_timestamp": "2020-09-23 04:01:09.540004", "matched_timestamp": "2020-09-23 04:01:09.540062"}
{"sample.message": [], "sample.message2": [], "raw_log_line": "[APPL] Some unique message", "system_timestamp": "2020-09-23 04:01:09.540079", "matched_timestamp": "2020-09-23 04:01:09.540135"}
{"sample.message": [], "sample.message2": [], "raw_log_line": "[APPL] Some unique message", "system_timestamp": "2020-09-23 04:01:09.540152", "matched_timestamp": "2020-09-23 04:01:09.540207"}
{"sample.message": [], "sample.message2": [], "raw_log_line": "[APPL] Some unique message", "system_timestamp": "2020-09-23 04:01:09.540224", "matched_timestamp": "2020-09-23 04:01:09.540279"}
{"sample.message": [], "sample.message2": [], "raw_log_line": "[APPL] Some unique message", "system_timestamp": "2020-09-23 04:01:09.540296", "matched_timestamp": "2020-09-23 04:01:09.540364"}
{"sample.message": [], "sample.message2": [], "raw_log_line": "[APPL] Some unique message", "system_timestamp": "2020-09-23 04:01:09.540384", "matched_timestamp": "2020-09-23 04:01:09.540621"}
{"sample.message": [], "sample.message2": [], "raw_log_line": "[APPL] Some unique message", "system_timestamp": "2020-09-23 04:01:09.540643", "matched_timestamp": "2020-09-23 04:01:09.540700"}
{"sample.message": [], "sample.message2": [], "raw_log_line": "[APPL] Some unique message", "system_timestamp": "2020-09-23 04:01:09.540717", "matched_timestamp": "2020-09-23 04:01:09.540771"}
"""

ALL_SAMPLE_EVENTS_TAC = b"""{"sample.message": [], "sample.message2": [], "raw_log_line": "[APPL] Some unique message", "system_timestamp": "2020-09-23 16:27:14.705267", "matched_timestamp": "2020-09-23 16:27:14.705322"}
{"sample.state": ["9"], "raw_log_line": "[APPL] Some other message with group data 9", "system_timestamp": "2020-09-23 16:27:14.705267", "matched_timestamp": "2020-09-23 16:27:14.705300"}
{"sample.message3": [], "raw_log_line": "[APPL] This is another message", "system_timestamp": "2020-09-23 16:27:14.705267", "matched_timestamp": "2020-09-23 16:27:14.705276"}
{"sample.message": [], "sample.message2": [], "raw_log_line": "[APPL] Some unique message", "system_timestamp": "2020-09-23 16:27:14.705192", "matched_timestamp": "2020-09-23 16:27:14.705249"}
{"sample.state": ["8"], "raw_log_line": "[APPL] Some other message with group data 8", "system_timestamp": "2020-09-23 16:27:14.705192", "matched_timestamp": "2020-09-23 16:27:14.705227"}
{"sample.message3": [], "raw_log_line": "[APPL] This is another message", "system_timestamp": "2020-09-23 16:27:14.705192", "matched_timestamp": "2020-09-23 16:27:14.705201"}
{"sample.message": [], "sample.message2": [], "raw_log_line": "[APPL] Some unique message", "system_timestamp": "2020-09-23 16:27:14.705002", "matched_timestamp": "2020-09-23 16:27:14.705169"}
{"sample.state": ["7"], "raw_log_line": "[APPL] Some other message with group data 7", "system_timestamp": "2020-09-23 16:27:14.705002", "matched_timestamp": "2020-09-23 16:27:14.705034"}
{"sample.message3": [], "raw_log_line": "[APPL] This is another message", "system_timestamp": "2020-09-23 16:27:14.705002", "matched_timestamp": "2020-09-23 16:27:14.705010"}
{"sample.message": [], "sample.message2": [], "raw_log_line": "[APPL] Some unique message", "system_timestamp": "2020-09-23 16:27:14.704930", "matched_timestamp": "2020-09-23 16:27:14.704984"}
{"sample.state": ["6"], "raw_log_line": "[APPL] Some other message with group data 6", "system_timestamp": "2020-09-23 16:27:14.704930", "matched_timestamp": "2020-09-23 16:27:14.704962"}
{"sample.message3": [], "raw_log_line": "[APPL] This is another message", "system_timestamp": "2020-09-23 16:27:14.704930", "matched_timestamp": "2020-09-23 16:27:14.704938"}
{"sample.message": [], "sample.message2": [], "raw_log_line": "[APPL] Some unique message", "system_timestamp": "2020-09-23 16:27:14.704858", "matched_timestamp": "2020-09-23 16:27:14.704912"}
{"sample.state": ["5"], "raw_log_line": "[APPL] Some other message with group data 5", "system_timestamp": "2020-09-23 16:27:14.704858", "matched_timestamp": "2020-09-23 16:27:14.704890"}
{"sample.message3": [], "raw_log_line": "[APPL] This is another message", "system_timestamp": "2020-09-23 16:27:14.704858", "matched_timestamp": "2020-09-23 16:27:14.704866"}
{"sample.message": [], "sample.message2": [], "raw_log_line": "[APPL] Some unique message", "system_timestamp": "2020-09-23 16:27:14.704785", "matched_timestamp": "2020-09-23 16:27:14.704840"}
{"sample.state": ["4"], "raw_log_line": "[APPL] Some other message with group data 4", "system_timestamp": "2020-09-23 16:27:14.704785", "matched_timestamp": "2020-09-23 16:27:14.704818"}
{"sample.message3": [], "raw_log_line": "[APPL] This is another message", "system_timestamp": "2020-09-23 16:27:14.704785", "matched_timestamp": "2020-09-23 16:27:14.704794"}
{"sample.message": [], "sample.message2": [], "raw_log_line": "[APPL] Some unique message", "system_timestamp": "2020-09-23 16:27:14.704712", "matched_timestamp": "2020-09-23 16:27:14.704768"}
{"sample.state": ["3"], "raw_log_line": "[APPL] Some other message with group data 3", "system_timestamp": "2020-09-23 16:27:14.704712", "matched_timestamp": "2020-09-23 16:27:14.704745"}
{"sample.message3": [], "raw_log_line": "[APPL] This is another message", "system_timestamp": "2020-09-23 16:27:14.704712", "matched_timestamp": "2020-09-23 16:27:14.704721"}
{"sample.message": [], "sample.message2": [], "raw_log_line": "[APPL] Some unique message", "system_timestamp": "2020-09-23 16:27:14.704637", "matched_timestamp": "2020-09-23 16:27:14.704694"}
{"sample.state": ["2"], "raw_log_line": "[APPL] Some other message with group data 2", "system_timestamp": "2020-09-23 16:27:14.704637", "matched_timestamp": "2020-09-23 16:27:14.704671"}
{"sample.message3": [], "raw_log_line": "[APPL] This is another message", "system_timestamp": "2020-09-23 16:27:14.704637", "matched_timestamp": "2020-09-23 16:27:14.704646"}
{"sample.message": [], "sample.message2": [], "raw_log_line": "[APPL] Some unique message", "system_timestamp": "2020-09-23 16:27:14.704558", "matched_timestamp": "2020-09-23 16:27:14.704618"}
{"sample.state": ["1"], "raw_log_line": "[APPL] Some other message with group data 1", "system_timestamp": "2020-09-23 16:27:14.704558", "matched_timestamp": "2020-09-23 16:27:14.704594"}
{"sample.message3": [], "raw_log_line": "[APPL] This is another message", "system_timestamp": "2020-09-23 16:27:14.704558", "matched_timestamp": "2020-09-23 16:27:14.704568"}
{"sample.message": [], "sample.message2": [], "raw_log_line": "[APPL] Some unique message", "system_timestamp": "2020-09-23 16:27:14.704424", "matched_timestamp": "2020-09-23 16:27:14.704537"}
{"sample.state": ["0"], "raw_log_line": "[APPL] Some other message with group data 0", "system_timestamp": "2020-09-23 16:27:14.704424", "matched_timestamp": "2020-09-23 16:27:14.704505"}
{"sample.message3": [], "raw_log_line": "[APPL] This is another message", "system_timestamp": "2020-09-23 16:27:14.704424", "matched_timestamp": "2020-09-23 16:27:14.704450"}
"""

SAMPLE_STATE_EVENTS = b"""{"sample.state": ["9"], "raw_log_line": "[APPL] Some other message with group data 9", "system_timestamp": "2020-09-23 17:12:48.881463", "matched_timestamp": "2020-09-23 17:12:48.881498"}
{"sample.state": ["8"], "raw_log_line": "[APPL] Some other message with group data 8", "system_timestamp": "2020-09-23 17:12:48.881386", "matched_timestamp": "2020-09-23 17:12:48.881421"}
{"sample.state": ["7"], "raw_log_line": "[APPL] Some other message with group data 7", "system_timestamp": "2020-09-23 17:12:48.881149", "matched_timestamp": "2020-09-23 17:12:48.881183"}
{"sample.state": ["6"], "raw_log_line": "[APPL] Some other message with group data 6", "system_timestamp": "2020-09-23 17:12:48.881076", "matched_timestamp": "2020-09-23 17:12:48.881109"}
{"sample.state": ["5"], "raw_log_line": "[APPL] Some other message with group data 5", "system_timestamp": "2020-09-23 17:12:48.881002", "matched_timestamp": "2020-09-23 17:12:48.881035"}
"""

BASIC_EVENTS = b"""{"basic.reboot_trigger": [], "system_timestamp": "2018-06-25 14:55:01.010453", "raw_log_line": "Note: GDM triggered reboot"}
{"basic.reboot_trigger": [], "system_timestamp": "2018-06-25 14:55:19.420630", "raw_log_line": "Note: GDM triggered reboot"}
{"basic.reboot_trigger": [], "system_timestamp": "2018-06-25 14:55:27.200832", "raw_log_line": "Note: GDM triggered reboot"}
"""

BASIC_FIRMWARE_EVENT = b"""{"basic.firmware_info": ["1.0.0"], "raw_log_line": "Bootloader 1.0.0", "system_timestamp": "2018-06-22 08:57:44.537463"}
"""

BASIC_REBOOT_TRIGGER_EVENT = b"""{"basic.reboot_trigger": [], "system_timestamp": "2018-06-22 08:57:44.304061", "raw_log_line": "Note: GDM triggered reboot"}
"""

BASIC_BOOTUP_EVENT = b"""{"basic.bootup": [], "system_timestamp": "2018-06-22 08:57:48.746996", "raw_log_line": "[0:00:00.059] [APPL] Welcome to Some App"}
"""

BASIC_BOOTUP_EVENTS = b"""{"basic.bootup": [], "system_timestamp": "2018-06-25 14:55:05.433307", "raw_log_line": "[0:00:00.055] [APPL] Welcome to Some App"}
{"basic.bootup": [], "system_timestamp": "2018-06-25 14:55:06.433307", "raw_log_line": "[0:00:00.055] [APPL] Welcome to Some App"}
{"basic.bootup": [], "system_timestamp": "2018-06-25 14:57:27.723463", "raw_log_line": "[0:00:00.055] [APPL] Welcome to Some App"}
{"basic.bootup": [], "system_timestamp": "2018-06-25 14:57:28.723463", "raw_log_line": "[0:00:00.055] [APPL] Welcome to Some App"}
{"basic.bootup": [], "system_timestamp": "2018-06-25 14:57:29.723463", "raw_log_line": "[0:00:00.055] [APPL] Welcome to Some App"}
{"basic.bootup": [], "system_timestamp": "2018-06-25 14:58:07.947229", "raw_log_line": "[0:00:00.055] [APPL] Welcome to Some App"}
"""

BASIC_BOOTUP_EVENTS_SUBSET = b"""{"basic.bootup": [], "system_timestamp": "2018-06-25 14:55:05.433307", "raw_log_line": "[0:00:00.055] [APPL] Welcome to Some App"}
{"basic.bootup": [], "system_timestamp": "2018-06-25 14:57:27.723463", "raw_log_line": "[0:00:00.055] [APPL] Welcome to Some App"}
{"basic.bootup": [], "system_timestamp": "2018-06-25 14:58:07.947229", "raw_log_line": "[0:00:00.055] [APPL] Welcome to Some App"}
"""
