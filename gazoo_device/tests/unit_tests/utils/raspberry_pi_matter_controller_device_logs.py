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

"""Device logs for raspberrypi_matter_controller devices."""

import copy
import textwrap

from gazoo_device.tests.unit_tests.utils import raspbian_device_logs
from gazoo_device.tests.unit_tests.utils import ssh_device_logs

generate_command = ssh_device_logs.generate_command
generate_response = ssh_device_logs.generate_response
make_device_responses = ssh_device_logs.make_device_responses

_COMMISSION_SUCCESS_RESPONSE = """
[1643754497.356221][5771:5776] CHIP:DMG: Received Command Response Data, Endpoint=0 Cluster=0x0000_0030 Command=0x0000_0005
[1643754497.356317][5771:5776] CHIP:ZCL: CommissioningCompleteResponse:
[1643754497.356340][5771:5776] CHIP:ZCL:   errorCode: 0
[1643754497.356361][5771:5776] CHIP:ZCL:   debugText:
[1643754497.356386][5771:5776] CHIP:CTL: Received success response 0x0
[1643754497.356445][5771:5776] CHIP:CTL: Rendezvous cleanup
[1643754497.356476][5771:5776] CHIP:TOO: Device commissioning completed with success
[1643754497.356557][5771:5776] CHIP:DMG: ICR moving to [AwaitingDe]
"""

_COMMAND_TIMEOUT_FAILURE = """
[1643830408.880736][9131:9136] CHIP:DL: CHIP task running
[1643830528.881208][9131:9131] CHIP:-: ../../examples/chip-tool/commands/common/CHIPCommand.cpp:248: CHIP Error 0x00000032: Timeout at ../../examples/chip-tool/commands/common/CHIPCommand.cpp:61
[1643830528.881315][9131:9131] CHIP:TOO: Run command failure: ../../examples/chip-tool/commands/common/CHIPCommand.cpp:248: CHIP Error 0x00000032: Timeout
[1643830528.893874][9131:9131] CHIP:SPT: VerifyOrDie failure at ../../examples/chip-tool/third_party/connectedhomeip/src/inet/InetLayer.h:121: sEndPointPool.Allocated() == 0
"""

_RESPONSES = ({
    "cmd": "which chip-tool",
    "resp": "/usr/local/bin/chip-tool",
    "code": 0,
}, {
    "cmd": "cat ~/.matter_sdk_version",
    "resp": "92f834375b2075e6c1c93d12b373b663d4b9250b",
    "code": "0",
}, {
    "cmd":
        "/usr/local/bin/chip-tool pairing ble-wifi 1234 hex:776966692d73736964 "
        "hex:776966692d70617373776f7264 20202021 3840",
    "resp": _COMMISSION_SUCCESS_RESPONSE,
    "code": 0,
}, {
    "cmd": "/usr/local/bin/chip-tool pairing onnetwork 1234 20202021",
    "resp": _COMMISSION_SUCCESS_RESPONSE,
    "code": 0,
}, {
    "cmd": "/usr/local/bin/chip-tool pairing onnetwork-long 1234 20202021 3840",
    "resp": _COMMISSION_SUCCESS_RESPONSE,
    "code": 0,
}, {
    "cmd": "/usr/local/bin/chip-tool pairing ble-thread 1234 hex:61626364 "
           "20202021 3840",
    "resp": _COMMISSION_SUCCESS_RESPONSE,
    "code": 0,
}, {
    "cmd": "/usr/local/bin/chip-tool pairing onnetwork 1234 00000000",
    "resp": _COMMAND_TIMEOUT_FAILURE,
    "code": 1,
}, {
    "cmd":
        "/usr/local/bin/chip-tool pairing unpair 1234",
    "resp":
        textwrap.dedent("""
            [1643829558.217384][8975:8980] CHIP:DL: CHIP task running
            [1643829558.217690][8975:8975] CHIP:CTL: Shutting down the commissioner
            [1643829558.217800][8975:8975] CHIP:CTL: Shutting down the controller
            [1643829558.217835][8975:8975] CHIP:CTL: Shutting down the commissioner
            [1643829558.217911][8975:8975] CHIP:CTL: Shutting down the controller
            [1643829558.217946][8975:8975] CHIP:CTL: Shutting down the commissioner
            [1643829558.218018][8975:8975] CHIP:CTL: Shutting down the controller
            [1643829558.218050][8975:8975] CHIP:CTL: Shutting down the commissioner
            [1643829558.218125][8975:8975] CHIP:CTL: Shutting down the controller
            [1643829558.218152][8975:8975] CHIP:CTL: Shutting down the System State, this will teardown the CHIP Stack
            [1643829558.218453][8975:8975] CHIP:BLE: BleConnectionDelegate::CancelConnection is not implemented.
            [1643829558.218743][8975:8975] CHIP:DL: writing settings to file (/tmp/chip_counters.ini-Kl4J8t)
            [1643829558.219431][8975:8975] CHIP:DL: renamed tmp file to file (/tmp/chip_counters.ini)
            [1643829558.219494][8975:8975] CHIP:DL: NVS set: chip-counters/total-operational-hours = 0 (0x0)
            [1643829558.219528][8975:8975] CHIP:DL: Inet Layer shutdown
            [1643829558.219551][8975:8975] CHIP:DL: BLE shutdown
            [1643829558.219573][8975:8975] CHIP:DL: System Layer shutdown
        """),
    "code":
        0,
}, {
    "cmd": "/usr/local/bin/chip-tool pairing unpair 0000",
    "resp": _COMMAND_TIMEOUT_FAILURE,
    "code": 1,
}, {
    "cmd":
        "/usr/local/bin/chip-tool onoff read on-time 1234 1",
    "resp":
        textwrap.dedent("""
            [1643757742.660018][6018:6023] CHIP:EM: Removed CHIP MessageCounter:7968535 from RetransTable on exchange 18935i
            [1643757742.660085][6018:6023] CHIP:DMG: ReportDataMessage =
            [1643757742.660114][6018:6023] CHIP:DMG: {
            [1643757742.660136][6018:6023] CHIP:DMG: 	AttributeReportIBs =
            [1643757742.660167][6018:6023] CHIP:DMG: 	[
            [1643757742.660192][6018:6023] CHIP:DMG: 		AttributeReportIB =
            [1643757742.660229][6018:6023] CHIP:DMG: 		{
            [1643757742.660255][6018:6023] CHIP:DMG: 			AttributeDataIB =
            [1643757742.660289][6018:6023] CHIP:DMG: 			{
            [1643757742.660323][6018:6023] CHIP:DMG: 				DataVersion = 0x0,
            [1643757742.660355][6018:6023] CHIP:DMG: 				AttributePathIB =
            [1643757742.660389][6018:6023] CHIP:DMG: 				{
            [1643757742.660425][6018:6023] CHIP:DMG: 					Endpoint = 0x1,
            [1643757742.660464][6018:6023] CHIP:DMG: 					Cluster = 0x6,
            [1643757742.660502][6018:6023] CHIP:DMG: 					Attribute = 0x0000_4001,
            [1643757742.660535][6018:6023] CHIP:DMG: 				}
            [1643757742.660570][6018:6023] CHIP:DMG:
            [1643757742.660605][6018:6023] CHIP:DMG: 					Data = 0,
            [1643757742.660638][6018:6023] CHIP:DMG: 			},
            [1643757742.660671][6018:6023] CHIP:DMG:
            [1643757742.660698][6018:6023] CHIP:DMG: 		},
            [1643757742.660731][6018:6023] CHIP:DMG:
            [1643757742.660755][6018:6023] CHIP:DMG: 	],
            [1643757742.660786][6018:6023] CHIP:DMG:
            [1643757742.660809][6018:6023] CHIP:DMG: 	SuppressResponse = true,
            [1643757742.660832][6018:6023] CHIP:DMG: }
            [1643757742.661022][6018:6023] CHIP:TOO: Endpoint: 1 Cluster: 0x0000_0006 Attribute 0x0000_4001
            [1643757742.661074][6018:6023] CHIP:TOO:   OnTime: 0
            [1643757742.661131][6018:6023] CHIP:EM: Sending Standalone Ack for MessageCounter:13418280 on exchange 18935i
        """),
    "code":
        0,
}, {
    "cmd":
        "/usr/local/bin/chip-tool onoff read on-off 1234 1",
    "resp":
        textwrap.dedent("""
            [1643757714.466937][6008:6013] CHIP:EM: Removed CHIP MessageCounter:2881700 from RetransTable on exchange 60917i
            [1643757714.467073][6008:6013] CHIP:DMG: ReportDataMessage =
            [1643757714.467140][6008:6013] CHIP:DMG: {
            [1643757714.467194][6008:6013] CHIP:DMG: 	AttributeReportIBs =
            [1643757714.467272][6008:6013] CHIP:DMG: 	[
            [1643757714.467332][6008:6013] CHIP:DMG: 		AttributeReportIB =
            [1643757714.467421][6008:6013] CHIP:DMG: 		{
            [1643757714.467486][6008:6013] CHIP:DMG: 			AttributeDataIB =
            [1643757714.467572][6008:6013] CHIP:DMG: 			{
            [1643757714.467653][6008:6013] CHIP:DMG: 				DataVersion = 0x0,
            [1643757714.467738][6008:6013] CHIP:DMG: 				AttributePathIB =
            [1643757714.467823][6008:6013] CHIP:DMG: 				{
            [1643757714.467900][6008:6013] CHIP:DMG: 					Endpoint = 0x1,
            [1643757714.467971][6008:6013] CHIP:DMG: 					Cluster = 0x6,
            [1643757714.468061][6008:6013] CHIP:DMG: 					Attribute = 0x0000_0000,
            [1643757714.468143][6008:6013] CHIP:DMG: 				}
            [1643757714.468234][6008:6013] CHIP:DMG:
            [1643757714.468313][6008:6013] CHIP:DMG: 					Data = true,
            [1643757714.468402][6008:6013] CHIP:DMG: 			},
            [1643757714.468488][6008:6013] CHIP:DMG:
            [1643757714.468556][6008:6013] CHIP:DMG: 		},
            [1643757714.468633][6008:6013] CHIP:DMG:
            [1643757714.468692][6008:6013] CHIP:DMG: 	],
            [1643757714.468767][6008:6013] CHIP:DMG:
            [1643757714.468827][6008:6013] CHIP:DMG: 	SuppressResponse = true,
            [1643757714.468956][6008:6013] CHIP:DMG: }
            [1643757714.469296][6008:6013] CHIP:TOO: Endpoint: 1 Cluster: 0x0000_0006 Attribute 0x0000_0000
            [1643757714.469413][6008:6013] CHIP:TOO:   OnOff: TRUE
            [1643757714.469533][6008:6013] CHIP:EM: Sending Standalone Ack for MessageCounter:3893373 on exchange 60917i
        """),
    "code":
        0,
}, {
    "cmd":
        "/usr/local/bin/chip-tool onoff write on-time 100 1234 1",
    "resp":
        textwrap.dedent("""
            [1643757763.344638][6025:6030] CHIP:DMG: WriteClient moving to [ResponseRe]
            [1643757763.344756][6025:6030] CHIP:DMG: WriteResponseMessage =
            [1643757763.344821][6025:6030] CHIP:DMG: {
            [1643757763.344875][6025:6030] CHIP:DMG: 	AttributeStatusIBs =
            [1643757763.345017][6025:6030] CHIP:DMG: 	[
            [1643757763.345079][6025:6030] CHIP:DMG: 		AttributeStatusIB =
            [1643757763.345154][6025:6030] CHIP:DMG: 		{
            [1643757763.345219][6025:6030] CHIP:DMG: 			AttributePathIB =
            [1643757763.345305][6025:6030] CHIP:DMG: 			{
            [1643757763.345387][6025:6030] CHIP:DMG: 				Endpoint = 0x1,
            [1643757763.345471][6025:6030] CHIP:DMG: 				Cluster = 0x6,
            [1643757763.345563][6025:6030] CHIP:DMG: 				Attribute = 0x0000_4001,
            [1643757763.345641][6025:6030] CHIP:DMG: 			}
            [1643757763.345731][6025:6030] CHIP:DMG:
            [1643757763.345809][6025:6030] CHIP:DMG: 			StatusIB =
            [1643757763.345892][6025:6030] CHIP:DMG: 			{
            [1643757763.345969][6025:6030] CHIP:DMG: 				status = 0x0,
            [1643757763.346052][6025:6030] CHIP:DMG: 			},
            [1643757763.346137][6025:6030] CHIP:DMG:
            [1643757763.346204][6025:6030] CHIP:DMG: 		},
            [1643757763.346285][6025:6030] CHIP:DMG:
            [1643757763.346344][6025:6030] CHIP:DMG: 	],
            [1643757763.346418][6025:6030] CHIP:DMG:
            [1643757763.346473][6025:6030] CHIP:DMG: }
            [1643757763.346621][6025:6030] CHIP:DMG: WriteClient moving to [AwaitingDe]
            [1643757763.346727][6025:6030] CHIP:EM: Sending Standalone Ack for MessageCounter:7207290 on exchange 63350i
        """),
    "code":
        0,
}, {
    "cmd":
        "/usr/local/bin/chip-tool onoff toggle  1234 1",
    "resp":
        textwrap.dedent("""
            [1643833410.401903][9308:9313] CHIP:DMG: ICR moving to [ResponseRe]
            [1643833410.401962][9308:9313] CHIP:DMG: InvokeResponseMessage =
            [1643833410.401988][9308:9313] CHIP:DMG: {
            [1643833410.402012][9308:9313] CHIP:DMG: 	suppressResponse = false,
            [1643833410.402040][9308:9313] CHIP:DMG: 	InvokeResponseIBs =
            [1643833410.402073][9308:9313] CHIP:DMG: 	[
            [1643833410.402097][9308:9313] CHIP:DMG: 		InvokeResponseIB =
            [1643833410.402133][9308:9313] CHIP:DMG: 		{
            [1643833410.402161][9308:9313] CHIP:DMG: 			CommandStatusIB =
            [1643833410.402194][9308:9313] CHIP:DMG: 			{
            [1643833410.402223][9308:9313] CHIP:DMG: 				CommandPathIB =
            [1643833410.402257][9308:9313] CHIP:DMG: 				{
            [1643833410.402291][9308:9313] CHIP:DMG: 					EndpointId = 0x1,
            [1643833410.402328][9308:9313] CHIP:DMG: 					ClusterId = 0x6,
            [1643833410.402360][9308:9313] CHIP:DMG: 					CommandId = 0x2,
            [1643833410.402395][9308:9313] CHIP:DMG: 				},
            [1643833410.402433][9308:9313] CHIP:DMG:
            [1643833410.402463][9308:9313] CHIP:DMG: 				StatusIB =
            [1643833410.402493][9308:9313] CHIP:DMG: 				{
            [1643833410.402524][9308:9313] CHIP:DMG: 					status = 0x0,
            [1643833410.402555][9308:9313] CHIP:DMG: 				},
            [1643833410.402588][9308:9313] CHIP:DMG:
            [1643833410.402618][9308:9313] CHIP:DMG: 			},
            [1643833410.402653][9308:9313] CHIP:DMG:
            [1643833410.402680][9308:9313] CHIP:DMG: 		},
            [1643833410.402713][9308:9313] CHIP:DMG:
            [1643833410.402736][9308:9313] CHIP:DMG: 	],
            [1643833410.402771][9308:9313] CHIP:DMG:
            [1643833410.402794][9308:9313] CHIP:DMG: },
            [1643833410.402857][9308:9313] CHIP:DMG: Received Command Response Status for Endpoint=1 Cluster=0x0000_0006 Command=0x0000_0002 Status=0x0
            [1643833410.402893][9308:9313] CHIP:DMG: ICR moving to [AwaitingDe]
        """),
    "code":
        0,
}, {
    "cmd":
        "/usr/local/bin/chip-tool onoff write non-existent-attr 100 1234 1",
    "resp":
        textwrap.dedent("""
            [1643757763.344638][6025:6030] CHIP:DMG: WriteClient moving to [ResponseRe]
            [1643757763.344756][6025:6030] CHIP:DMG: WriteResponseMessage =
            [1643757763.344821][6025:6030] CHIP:DMG: {
            [1643757763.344875][6025:6030] CHIP:DMG: 	AttributeStatusIBs =
            [1643757763.345017][6025:6030] CHIP:DMG: 	[
            [1643757763.345079][6025:6030] CHIP:DMG: 		AttributeStatusIB =
            [1643757763.345154][6025:6030] CHIP:DMG: 		{
            [1643757763.345219][6025:6030] CHIP:DMG: 			AttributePathIB =
            [1643757763.345305][6025:6030] CHIP:DMG: 			{
            [1643757763.345387][6025:6030] CHIP:DMG: 				Endpoint = 0x1,
            [1643757763.345471][6025:6030] CHIP:DMG: 				Cluster = 0x6,
            [1643757763.345563][6025:6030] CHIP:DMG: 				Attribute = 0x0000_4001,
            [1643757763.345641][6025:6030] CHIP:DMG: 			}
            [1643757763.345731][6025:6030] CHIP:DMG:
            [1643757763.345809][6025:6030] CHIP:DMG: 			StatusIB =
            [1643757763.345892][6025:6030] CHIP:DMG: 			{
            [1643757763.345969][6025:6030] CHIP:DMG: 				status = 0x1234,
            [1643757763.346052][6025:6030] CHIP:DMG: 			},
            [1643757763.346137][6025:6030] CHIP:DMG:
            [1643757763.346204][6025:6030] CHIP:DMG: 		},
            [1643757763.346285][6025:6030] CHIP:DMG:
            [1643757763.346344][6025:6030] CHIP:DMG: 	],
            [1643757763.346418][6025:6030] CHIP:DMG:
            [1643757763.346473][6025:6030] CHIP:DMG: }
            [1643757763.346621][6025:6030] CHIP:DMG: WriteClient moving to [AwaitingDe]
            [1643757763.346727][6025:6030] CHIP:EM: Sending Standalone Ack for MessageCounter:7207290 on exchange 63350i
        """),
    "code":
        1,
}, {
    "cmd":
        "/usr/local/bin/chip-tool onoff non-existent-cmd  1234 1",
    "resp":
        textwrap.dedent("""
            [1643833410.401903][9308:9313] CHIP:DMG: ICR moving to [ResponseRe]
            [1643833410.401962][9308:9313] CHIP:DMG: InvokeResponseMessage =
            [1643833410.401988][9308:9313] CHIP:DMG: {
            [1643833410.402012][9308:9313] CHIP:DMG: 	suppressResponse = false,
            [1643833410.402040][9308:9313] CHIP:DMG: 	InvokeResponseIBs =
            [1643833410.402073][9308:9313] CHIP:DMG: 	[
            [1643833410.402097][9308:9313] CHIP:DMG: 		InvokeResponseIB =
            [1643833410.402133][9308:9313] CHIP:DMG: 		{
            [1643833410.402161][9308:9313] CHIP:DMG: 			CommandStatusIB =
            [1643833410.402194][9308:9313] CHIP:DMG: 			{
            [1643833410.402223][9308:9313] CHIP:DMG: 				CommandPathIB =
            [1643833410.402257][9308:9313] CHIP:DMG: 				{
            [1643833410.402291][9308:9313] CHIP:DMG: 					EndpointId = 0x1,
            [1643833410.402328][9308:9313] CHIP:DMG: 					ClusterId = 0x6,
            [1643833410.402360][9308:9313] CHIP:DMG: 					CommandId = 0x2,
            [1643833410.402395][9308:9313] CHIP:DMG: 				},
            [1643833410.402433][9308:9313] CHIP:DMG:
            [1643833410.402463][9308:9313] CHIP:DMG: 				StatusIB =
            [1643833410.402493][9308:9313] CHIP:DMG: 				{
            [1643833410.402524][9308:9313] CHIP:DMG: 					status = 0x1234,
            [1643833410.402555][9308:9313] CHIP:DMG: 				},
            [1643833410.402588][9308:9313] CHIP:DMG:
            [1643833410.402618][9308:9313] CHIP:DMG: 			},
            [1643833410.402653][9308:9313] CHIP:DMG:
            [1643833410.402680][9308:9313] CHIP:DMG: 		},
            [1643833410.402713][9308:9313] CHIP:DMG:
            [1643833410.402736][9308:9313] CHIP:DMG: 	],
            [1643833410.402771][9308:9313] CHIP:DMG:
            [1643833410.402794][9308:9313] CHIP:DMG: },
            [1643833410.402857][9308:9313] CHIP:DMG: Received Command Response Status for Endpoint=1 Cluster=0x0000_0006 Command=0x0000_0002 Status=0x0
            [1643833410.402893][9308:9313] CHIP:DMG: ICR moving to [AwaitingDe]
        """),
    "code":
        1,
}, {
    "cmd": "echo 1234 > ~/.matter_sdk_version",
    "resp": "",
    "code": 0,
})

DEFAULT_BEHAVIOR = copy.deepcopy(raspbian_device_logs.DEFAULT_BEHAVIOR)
DEFAULT_BEHAVIOR.update(ssh_device_logs.make_device_responses(_RESPONSES))
