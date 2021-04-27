# Copyright 2021 Google LLC
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

"""Transport properties that can be read or written to for various transports."""

# Common properties
AUTO_REOPEN = "auto_reopen"
OPEN_ON_START = "open_on_start"

# ProcessTransport properties
CLOSE_FDS = "close_fds"

# SerialTransport properties
BAUDRATE = "baudrate"
BYTESIZE = "bytesize"
PARITY = "parity"
STOPBITS = "stopbits"
XONXOFF = "xonxoff"
RTSCTS = "rtscts"
DSRDTR = "dsrdtr"
EXCLUSIVE = "exclusive"
READ_REOPEN = "read_reopen"
USE_HIGH_BAUDRATE_FLOW_CONTROL = "use_high_baudrate_flow_control"

# TcpTransport properties
HOST = "host"
PORT = "port"

# TcpTransport, WebSocketTransport properties
CONNECT_TIMEOUT = "connect_timeout"

# WebSocketTransport properties
WEBSOCKET_URL = "websocket_url"
