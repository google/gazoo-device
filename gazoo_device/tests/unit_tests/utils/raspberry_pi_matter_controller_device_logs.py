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

import textwrap

from gazoo_device.tests.unit_tests.utils import raspbian_device_logs
from gazoo_device.tests.unit_tests.utils import ssh_device_logs
from immutabledict import immutabledict

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

DESCRIPTOR_DEVICE_LIST_COMMAND = ("/usr/local/bin/chip-tool descriptor read "
                                  "device-list 1234 1")
DESCRIPTOR_DEVICE_LIST_RESPONSE = textwrap.dedent("""
    [1653012107.332640][1030544:1030549] CHIP:EM: Removed CHIP MessageCounter:519807 from RetransTable on exchange 35121i
    [1653012107.332703][1030544:1030549] CHIP:DMG: ReportDataMessage =
    [1653012107.332744][1030544:1030549] CHIP:DMG: {{
    [1653012107.332777][1030544:1030549] CHIP:DMG: 	AttributeReportIBs =
    [1653012107.332809][1030544:1030549] CHIP:DMG: 	[
    [1653012107.332833][1030544:1030549] CHIP:DMG: 		AttributeReportIB =
    [1653012107.332877][1030544:1030549] CHIP:DMG: 		{{
    [1653012107.332903][1030544:1030549] CHIP:DMG: 			AttributeDataIB =
    [1653012107.332947][1030544:1030549] CHIP:DMG: 			{{
    [1653012107.332988][1030544:1030549] CHIP:DMG: 				DataVersion = 0xd1eb3728,
    [1653012107.333020][1030544:1030549] CHIP:DMG: 				AttributePathIB =
    [1653012107.333062][1030544:1030549] CHIP:DMG: 				{{
    [1653012107.333110][1030544:1030549] CHIP:DMG: 					Endpoint = 0x1,
    [1653012107.333145][1030544:1030549] CHIP:DMG: 					Cluster = 0x1d,
    [1653012107.333193][1030544:1030549] CHIP:DMG: 					Attribute = 0x0000_0000,
    [1653012107.333238][1030544:1030549] CHIP:DMG: 				}}
    [1653012107.333279][1030544:1030549] CHIP:DMG:
    [1653012107.333311][1030544:1030549] CHIP:DMG: 					Data = [
    [1653012107.333350][1030544:1030549] CHIP:DMG:
    [1653012107.333396][1030544:1030549] CHIP:DMG: 					],
    [1653012107.333432][1030544:1030549] CHIP:DMG: 			}},
    [1653012107.333475][1030544:1030549] CHIP:DMG:
    [1653012107.333502][1030544:1030549] CHIP:DMG: 		}},
    [1653012107.333553][1030544:1030549] CHIP:DMG:
    [1653012107.333586][1030544:1030549] CHIP:DMG: 		AttributeReportIB =
    [1653012107.333622][1030544:1030549] CHIP:DMG: 		{{
    [1653012107.333657][1030544:1030549] CHIP:DMG: 			AttributeDataIB =
    [1653012107.333688][1030544:1030549] CHIP:DMG: 			{{
    [1653012107.333730][1030544:1030549] CHIP:DMG: 				DataVersion = 0xd1eb3728,
    [1653012107.333770][1030544:1030549] CHIP:DMG: 				AttributePathIB =
    [1653012107.333804][1030544:1030549] CHIP:DMG: 				{{
    [1653012107.333846][1030544:1030549] CHIP:DMG: 					Endpoint = 0x1,
    [1653012107.333892][1030544:1030549] CHIP:DMG: 					Cluster = 0x1d,
    [1653012107.333931][1030544:1030549] CHIP:DMG: 					Attribute = 0x0000_0000,
    [1653012107.333973][1030544:1030549] CHIP:DMG: 					ListIndex = Null,
    [1653012107.334017][1030544:1030549] CHIP:DMG: 				}}
    [1653012107.334053][1030544:1030549] CHIP:DMG:
    [1653012107.334093][1030544:1030549] CHIP:DMG: 					Data =
    [1653012107.334137][1030544:1030549] CHIP:DMG: 					{{
    [1653012107.334170][1030544:1030549] CHIP:DMG: 						0x0 = {DEVICE_TYPE_ID},
    [1653012107.334219][1030544:1030549] CHIP:DMG: 						0x1 = 1,
    [1653012107.334265][1030544:1030549] CHIP:DMG: 					}},
    [1653012107.334304][1030544:1030549] CHIP:DMG: 			}},
    [1653012107.334341][1030544:1030549] CHIP:DMG:
    [1653012107.334375][1030544:1030549] CHIP:DMG: 		}},
    [1653012107.334404][1030544:1030549] CHIP:DMG:
    [1653012107.334424][1030544:1030549] CHIP:DMG: 	],
    [1653012107.334465][1030544:1030549] CHIP:DMG:
    [1653012107.334491][1030544:1030549] CHIP:DMG: 	SuppressResponse = true,
    [1653012107.334524][1030544:1030549] CHIP:DMG: 	InteractionModelRevision = 1
    [1653012107.334558][1030544:1030549] CHIP:DMG: }}
    [1653012107.334866][1030544:1030549] CHIP:TOO: Endpoint: 2 Cluster: 0x0000_001D Attribute 0x0000_0000 DataVersion: 3521853224
    [1653012107.334929][1030544:1030549] CHIP:TOO:   device list: 1 entries
    [1653012107.334973][1030544:1030549] CHIP:TOO:     [1]: {{
    [1653012107.334997][1030544:1030549] CHIP:TOO:       Type: {DEVICE_TYPE_ID}
    [1653012107.335030][1030544:1030549] CHIP:TOO:       Revision: 1
    [1653012107.335053][1030544:1030549] CHIP:TOO:      }}
""")

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
    "cmd": "/usr/local/bin/chip-tool pairing ble-thread 1234 hex:abcd "
           "20202021 3840",
    "resp": _COMMISSION_SUCCESS_RESPONSE,
    "code": 0,
}, {
    "cmd": "/usr/local/bin/chip-tool pairing onnetwork 1234 20202021 "
           "--paa-trust-store-path "
           "/home/pi/credentials/development/paa-root-certs",
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
        ("/usr/local/bin/chip-tool doorlock lock-door  1234 1 "
         "--timedInteractionTimeoutMs 1000"),
    "resp":
        textwrap.dedent("""
            [1660950609.491083][2194063:2194068] CHIP:DMG: ICR moving to [ResponseRe]
            [1660950609.491192][2194063:2194068] CHIP:DMG: InvokeResponseMessage =
            [1660950609.491257][2194063:2194068] CHIP:DMG: {
            [1660950609.491320][2194063:2194068] CHIP:DMG: 	suppressResponse = false,
            [1660950609.491384][2194063:2194068] CHIP:DMG: 	InvokeResponseIBs =
            [1660950609.491469][2194063:2194068] CHIP:DMG: 	[
            [1660950609.491534][2194063:2194068] CHIP:DMG: 		InvokeResponseIB =
            [1660950609.491677][2194063:2194068] CHIP:DMG: 		{
            [1660950609.491751][2194063:2194068] CHIP:DMG: 			CommandStatusIB =
            [1660950609.491834][2194063:2194068] CHIP:DMG: 			{
            [1660950609.491921][2194063:2194068] CHIP:DMG: 				CommandPathIB =
            [1660950609.492010][2194063:2194068] CHIP:DMG: 				{
            [1660950609.492103][2194063:2194068] CHIP:DMG: 					EndpointId = 0x1,
            [1660950609.492198][2194063:2194068] CHIP:DMG: 					ClusterId = 0x101,
            [1660950609.492289][2194063:2194068] CHIP:DMG: 					CommandId = 0x0,
            [1660950609.492375][2194063:2194068] CHIP:DMG: 				},
            [1660950609.492481][2194063:2194068] CHIP:DMG:
            [1660950609.492561][2194063:2194068] CHIP:DMG: 				StatusIB =
            [1660950609.492649][2194063:2194068] CHIP:DMG: 				{
            [1660950609.492739][2194063:2194068] CHIP:DMG: 					status = 0x00 (SUCCESS),
            [1660950609.492826][2194063:2194068] CHIP:DMG: 				},
            [1660950609.492921][2194063:2194068] CHIP:DMG:
            [1660950609.492998][2194063:2194068] CHIP:DMG: 			},
            [1660950609.493087][2194063:2194068] CHIP:DMG:
            [1660950609.493159][2194063:2194068] CHIP:DMG: 		},
            [1660950609.493241][2194063:2194068] CHIP:DMG:
            [1660950609.493302][2194063:2194068] CHIP:DMG: 	],
            [1660950609.493382][2194063:2194068] CHIP:DMG:
            [1660950609.493445][2194063:2194068] CHIP:DMG: 	InteractionModelRevision = 1
            [1660950609.493506][2194063:2194068] CHIP:DMG: },
            [1660950609.493658][2194063:2194068] CHIP:DMG: Received Command Response Status for Endpoint=1 Cluster=0x0000_0101 Command=0x0000_0000 Status=0x0
            [1660950609.493768][2194063:2194068] CHIP:DMG: ICR moving to [AwaitingDe]
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
    "cmd":
        "/usr/local/bin/chip-tool descriptor read parts-list 1234 0",
    "resp":
        textwrap.dedent("""
            [1653012051.833688][1030538:1030543] CHIP:EM: Removed CHIP MessageCounter:9561517 from RetransTable on exchange 19272i
            [1653012051.833755][1030538:1030543] CHIP:DMG: ReportDataMessage =
            [1653012051.833797][1030538:1030543] CHIP:DMG: {
            [1653012051.833819][1030538:1030543] CHIP:DMG: 	AttributeReportIBs =
            [1653012051.833860][1030538:1030543] CHIP:DMG: 	[
            [1653012051.833886][1030538:1030543] CHIP:DMG: 		AttributeReportIB =
            [1653012051.833931][1030538:1030543] CHIP:DMG: 		{
            [1653012051.833959][1030538:1030543] CHIP:DMG: 			AttributeDataIB =
            [1653012051.834003][1030538:1030543] CHIP:DMG: 			{
            [1653012051.834045][1030538:1030543] CHIP:DMG: 				DataVersion = 0xc700158c,
            [1653012051.834077][1030538:1030543] CHIP:DMG: 				AttributePathIB =
            [1653012051.834120][1030538:1030543] CHIP:DMG: 				{
            [1653012051.834162][1030538:1030543] CHIP:DMG: 					Endpoint = 0x0,
            [1653012051.834206][1030538:1030543] CHIP:DMG: 					Cluster = 0x1d,
            [1653012051.834242][1030538:1030543] CHIP:DMG: 					Attribute = 0x0000_0003,
            [1653012051.834285][1030538:1030543] CHIP:DMG: 				}
            [1653012051.834321][1030538:1030543] CHIP:DMG:
            [1653012051.834362][1030538:1030543] CHIP:DMG: 					Data = [
            [1653012051.834396][1030538:1030543] CHIP:DMG:
            [1653012051.834439][1030538:1030543] CHIP:DMG: 					],
            [1653012051.834476][1030538:1030543] CHIP:DMG: 			},
            [1653012051.834510][1030538:1030543] CHIP:DMG:
            [1653012051.834546][1030538:1030543] CHIP:DMG: 		},
            [1653012051.834586][1030538:1030543] CHIP:DMG:
            [1653012051.834619][1030538:1030543] CHIP:DMG: 		AttributeReportIB =
            [1653012051.834654][1030538:1030543] CHIP:DMG: 		{
            [1653012051.834690][1030538:1030543] CHIP:DMG: 			AttributeDataIB =
            [1653012051.834723][1030538:1030543] CHIP:DMG: 			{
            [1653012051.834763][1030538:1030543] CHIP:DMG: 				DataVersion = 0xc700158c,
            [1653012051.834795][1030538:1030543] CHIP:DMG: 				AttributePathIB =
            [1653012051.834838][1030538:1030543] CHIP:DMG: 				{
            [1653012051.834872][1030538:1030543] CHIP:DMG: 					Endpoint = 0x0,
            [1653012051.834919][1030538:1030543] CHIP:DMG: 					Cluster = 0x1d,
            [1653012051.834958][1030538:1030543] CHIP:DMG: 					Attribute = 0x0000_0003,
            [1653012051.835001][1030538:1030543] CHIP:DMG: 					ListIndex = Null,
            [1653012051.835033][1030538:1030543] CHIP:DMG: 				}
            [1653012051.835077][1030538:1030543] CHIP:DMG:
            [1653012051.835110][1030538:1030543] CHIP:DMG: 					Data = 1,
            [1653012051.835155][1030538:1030543] CHIP:DMG: 			},
            [1653012051.835189][1030538:1030543] CHIP:DMG:
            [1653012051.835216][1030538:1030543] CHIP:DMG: 		},
            [1653012051.835265][1030538:1030543] CHIP:DMG:
            [1653012051.835975][1030538:1030543] CHIP:DMG: 	],
            [1653012051.836024][1030538:1030543] CHIP:DMG:
            [1653012051.836050][1030538:1030543] CHIP:DMG: 	SuppressResponse = true,
            [1653012051.836085][1030538:1030543] CHIP:DMG: 	InteractionModelRevision = 1
            [1653012051.836108][1030538:1030543] CHIP:DMG: }
            [1653012051.836478][1030538:1030543] CHIP:TOO: Endpoint: 0 Cluster: 0x0000_001D Attribute 0x0000_0003 DataVersion: 3338671500
            [1653012051.836538][1030538:1030543] CHIP:TOO:   parts list: 1 entries
            [1653012051.836568][1030538:1030543] CHIP:TOO:     [1]: 1
        """),
    "code":
        0,
}, {
    "cmd": "/usr/local/bin/chip-tool descriptor read device-list 1234 0",
    "resp": DESCRIPTOR_DEVICE_LIST_RESPONSE.format(DEVICE_TYPE_ID=22),
    "code": 0,
}, {
    "cmd": DESCRIPTOR_DEVICE_LIST_COMMAND,
    "resp": DESCRIPTOR_DEVICE_LIST_RESPONSE.format(DEVICE_TYPE_ID=256),
    "code": 0,
}, {
    "cmd":
        "/usr/local/bin/chip-tool descriptor read server-list 1234 1",
    "resp":
        textwrap.dedent("""
            [1653012222.678497][1030572:1030577] CHIP:EM: Removed CHIP MessageCounter:8097092 from RetransTable on exchange 42291i
            [1653012222.678733][1030572:1030577] CHIP:DMG: ReportDataMessage =
            [1653012222.678762][1030572:1030577] CHIP:DMG: {
            [1653012222.678783][1030572:1030577] CHIP:DMG: 	AttributeReportIBs =
            [1653012222.678815][1030572:1030577] CHIP:DMG: 	[
            [1653012222.678839][1030572:1030577] CHIP:DMG: 		AttributeReportIB =
            [1653012222.678884][1030572:1030577] CHIP:DMG: 		{
            [1653012222.678918][1030572:1030577] CHIP:DMG: 			AttributeDataIB =
            [1653012222.678954][1030572:1030577] CHIP:DMG: 			{
            [1653012222.678999][1030572:1030577] CHIP:DMG: 				DataVersion = 0xc7508647,
            [1653012222.679037][1030572:1030577] CHIP:DMG: 				AttributePathIB =
            [1653012222.679065][1030572:1030577] CHIP:DMG: 				{
            [1653012222.679095][1030572:1030577] CHIP:DMG: 					Endpoint = 0x1,
            [1653012222.679124][1030572:1030577] CHIP:DMG: 					Cluster = 0x1d,
            [1653012222.679161][1030572:1030577] CHIP:DMG: 					Attribute = 0x0000_0001,
            [1653012222.679200][1030572:1030577] CHIP:DMG: 				}
            [1653012222.679236][1030572:1030577] CHIP:DMG:
            [1653012222.679278][1030572:1030577] CHIP:DMG: 					Data = [
            [1653012222.679309][1030572:1030577] CHIP:DMG:
            [1653012222.679352][1030572:1030577] CHIP:DMG: 					],
            [1653012222.679394][1030572:1030577] CHIP:DMG: 			},
            [1653012222.679428][1030572:1030577] CHIP:DMG:
            [1653012222.679463][1030572:1030577] CHIP:DMG: 		},
            [1653012222.679510][1030572:1030577] CHIP:DMG:
            [1653012222.679535][1030572:1030577] CHIP:DMG: 		AttributeReportIB =
            [1653012222.679575][1030572:1030577] CHIP:DMG: 		{
            [1653012222.679601][1030572:1030577] CHIP:DMG: 			AttributeDataIB =
            [1653012222.679640][1030572:1030577] CHIP:DMG: 			{
            [1653012222.679700][1030572:1030577] CHIP:DMG: 				DataVersion = 0xc7508647,
            [1653012222.679732][1030572:1030577] CHIP:DMG: 				AttributePathIB =
            [1653012222.679772][1030572:1030577] CHIP:DMG: 				{
            [1653012222.679815][1030572:1030577] CHIP:DMG: 					Endpoint = 0x1,
            [1653012222.679848][1030572:1030577] CHIP:DMG: 					Cluster = 0x1d,
            [1653012222.679891][1030572:1030577] CHIP:DMG: 					Attribute = 0x0000_0001,
            [1653012222.679943][1030572:1030577] CHIP:DMG: 					ListIndex = Null,
            [1653012222.679969][1030572:1030577] CHIP:DMG: 				}
            [1653012222.680011][1030572:1030577] CHIP:DMG:
            [1653012222.680056][1030572:1030577] CHIP:DMG: 					Data = 3,
            [1653012222.680088][1030572:1030577] CHIP:DMG: 			},
            [1653012222.680128][1030572:1030577] CHIP:DMG:
            [1653012222.680153][1030572:1030577] CHIP:DMG: 		},
            [1653012222.680199][1030572:1030577] CHIP:DMG:
            [1653012222.681618][1030572:1030577] CHIP:DMG: 		AttributeReportIB =
            [1653012222.681650][1030572:1030577] CHIP:DMG: 		{
            [1653012222.681684][1030572:1030577] CHIP:DMG: 			AttributeDataIB =
            [1653012222.681712][1030572:1030577] CHIP:DMG: 			{
            [1653012222.681751][1030572:1030577] CHIP:DMG: 				DataVersion = 0xc7508647,
            [1653012222.681785][1030572:1030577] CHIP:DMG: 				AttributePathIB =
            [1653012222.681828][1030572:1030577] CHIP:DMG: 				{
            [1653012222.681867][1030572:1030577] CHIP:DMG: 					Endpoint = 0x1,
            [1653012222.681903][1030572:1030577] CHIP:DMG: 					Cluster = 0x1d,
            [1653012222.681947][1030572:1030577] CHIP:DMG: 					Attribute = 0x0000_0001,
            [1653012222.681988][1030572:1030577] CHIP:DMG: 					ListIndex = Null,
            [1653012222.682020][1030572:1030577] CHIP:DMG: 				}
            [1653012222.682066][1030572:1030577] CHIP:DMG:
            [1653012222.682111][1030572:1030577] CHIP:DMG: 					Data = 6,
            [1653012222.682152][1030572:1030577] CHIP:DMG: 			},
            [1653012222.682186][1030572:1030577] CHIP:DMG:
            [1653012222.682222][1030572:1030577] CHIP:DMG: 		},
            [1653012222.682267][1030572:1030577] CHIP:DMG:
            [1653012222.702070][1030572:1030577] CHIP:DMG: 	],
            [1653012222.702275][1030572:1030577] CHIP:DMG:
            [1653012222.702301][1030572:1030577] CHIP:DMG: 	MoreChunkedMessages = true,
            [1653012222.702326][1030572:1030577] CHIP:DMG: 	InteractionModelRevision = 1
            [1653012222.702349][1030572:1030577] CHIP:DMG: }
        """),
    "code":
        0,
}, {
    "cmd":
        "/usr/local/bin/chip-tool descriptor read server-list 1234 0",
    "resp":
        textwrap.dedent("""
            [1653012222.678497][1030572:1030577] CHIP:EM: Removed CHIP MessageCounter:8097092 from RetransTable on exchange 42291i
            [1653012222.678733][1030572:1030577] CHIP:DMG: ReportDataMessage =
            [1653012222.678762][1030572:1030577] CHIP:DMG: {
            [1653012222.678783][1030572:1030577] CHIP:DMG: 	AttributeReportIBs =
            [1653012222.678815][1030572:1030577] CHIP:DMG: 	[
            [1653012222.678839][1030572:1030577] CHIP:DMG: 		AttributeReportIB =
            [1653012222.678884][1030572:1030577] CHIP:DMG: 		{
            [1653012222.678918][1030572:1030577] CHIP:DMG: 			AttributeDataIB =
            [1653012222.678954][1030572:1030577] CHIP:DMG: 			{
            [1653012222.678999][1030572:1030577] CHIP:DMG: 				DataVersion = 0xc7508647,
            [1653012222.679037][1030572:1030577] CHIP:DMG: 				AttributePathIB =
            [1653012222.679065][1030572:1030577] CHIP:DMG: 				{
            [1653012222.679095][1030572:1030577] CHIP:DMG: 					Endpoint = 0x1,
            [1653012222.679124][1030572:1030577] CHIP:DMG: 					Cluster = 0x1d,
            [1653012222.679161][1030572:1030577] CHIP:DMG: 					Attribute = 0x0000_0001,
            [1653012222.679200][1030572:1030577] CHIP:DMG: 				}
            [1653012222.679236][1030572:1030577] CHIP:DMG:
            [1653012222.679278][1030572:1030577] CHIP:DMG: 					Data = [
            [1653012222.679309][1030572:1030577] CHIP:DMG:
            [1653012222.679352][1030572:1030577] CHIP:DMG: 					],
            [1653012222.679394][1030572:1030577] CHIP:DMG: 			},
            [1653012222.679428][1030572:1030577] CHIP:DMG:
            [1653012222.679463][1030572:1030577] CHIP:DMG: 		},
            [1653012222.679510][1030572:1030577] CHIP:DMG:
            [1653012222.679535][1030572:1030577] CHIP:DMG: 		AttributeReportIB =
            [1653012222.679575][1030572:1030577] CHIP:DMG: 		{
            [1653012222.679601][1030572:1030577] CHIP:DMG: 			AttributeDataIB =
            [1653012222.679640][1030572:1030577] CHIP:DMG: 			{
            [1653012222.679700][1030572:1030577] CHIP:DMG: 				DataVersion = 0xc7508647,
            [1653012222.679732][1030572:1030577] CHIP:DMG: 				AttributePathIB =
            [1653012222.679772][1030572:1030577] CHIP:DMG: 				{
            [1653012222.679815][1030572:1030577] CHIP:DMG: 					Endpoint = 0x1,
            [1653012222.679848][1030572:1030577] CHIP:DMG: 					Cluster = 0x1d,
            [1653012222.679891][1030572:1030577] CHIP:DMG: 					Attribute = 0x0000_0001,
            [1653012222.679943][1030572:1030577] CHIP:DMG: 					ListIndex = Null,
            [1653012222.679969][1030572:1030577] CHIP:DMG: 				}
            [1653012222.680011][1030572:1030577] CHIP:DMG:
            [1653012222.680056][1030572:1030577] CHIP:DMG: 					Data = 40,
            [1653012222.680088][1030572:1030577] CHIP:DMG: 			},
            [1653012222.680128][1030572:1030577] CHIP:DMG:
            [1653012222.680153][1030572:1030577] CHIP:DMG: 		},
            [1653012222.682267][1030572:1030577] CHIP:DMG:
            [1653012222.702070][1030572:1030577] CHIP:DMG: 	],
            [1653012222.702275][1030572:1030577] CHIP:DMG:
            [1653012222.702301][1030572:1030577] CHIP:DMG: 	MoreChunkedMessages = true,
            [1653012222.702326][1030572:1030577] CHIP:DMG: 	InteractionModelRevision = 1
            [1653012222.702349][1030572:1030577] CHIP:DMG: }
        """),
    "code":
        0,
}, {
    "cmd": "echo 1234 > ~/.matter_sdk_version",
    "resp": "",
    "code": 0,
}, {
    "cmd": "rm -rf /tmp/chip*",
    "resp": "",
    "code": 0,
}, {
    "cmd": "/usr/local/bin/chip-tool storage clear-all",
    "resp":
        "[1658180504.043668][493408:493408] CHIP:TOO: Clearing Default storage",
    "code": 0,
}, {
    "cmd":
        "/usr/local/bin/chip-tool onoff read string-attr 1234 1",
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
            [1643757714.468313][6008:6013] CHIP:DMG: 					Data = "TEST_VENDOR" (11 chars),
            [1643757714.468402][6008:6013] CHIP:DMG: 			},
            [1643757714.468488][6008:6013] CHIP:DMG:
            [1643757714.468556][6008:6013] CHIP:DMG: 		},
            [1643757714.468633][6008:6013] CHIP:DMG:
            [1643757714.468692][6008:6013] CHIP:DMG: 	],
            [1643757714.468767][6008:6013] CHIP:DMG:
            [1643757714.468827][6008:6013] CHIP:DMG: 	SuppressResponse = true,
            [1643757714.468956][6008:6013] CHIP:DMG: }
            [1643757714.469296][6008:6013] CHIP:TOO: Endpoint: 1 Cluster: 0x0000_0006 Attribute 0x0000_0000
            [1643757714.469413][6008:6013] CHIP:TOO:   VendorName: TEST_VENDOR
            [1643757714.469533][6008:6013] CHIP:EM: Sending Standalone Ack for MessageCounter:3893373 on exchange 60917i
        """),
    "code":
        0,
})

DEFAULT_BEHAVIOR = immutabledict({
    **raspbian_device_logs.DEFAULT_BEHAVIOR,
    **ssh_device_logs.make_device_responses(_RESPONSES)
})
