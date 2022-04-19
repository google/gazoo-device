# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: wifi_service.proto
# pylint: skip-file
"""Generated protocol buffer code."""
from google.protobuf.internal import enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from gazoo_device.protos import common_pb2 as common__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='wifi_service.proto',
  package='chip.rpc',
  syntax='proto3',
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_pb=b'\n\x12wifi_service.proto\x12\x08\x63hip.rpc\x1a\x0c\x63ommon.proto\"\x1a\n\x07\x43hannel\x12\x0f\n\x07\x63hannel\x18\x01 \x01(\r\"\x14\n\x04Ssid\x12\x0c\n\x04ssid\x18\x01 \x01(\x0c\"\x1a\n\x05State\x12\x11\n\tconnected\x18\x01 \x01(\x08\"!\n\nMacAddress\x12\x13\n\x0bmac_address\x18\x01 \x01(\t\"\"\n\rWiFiInterface\x12\x11\n\tinterface\x18\x01 \x01(\t\"\x1d\n\nIP4Address\x12\x0f\n\x07\x61\x64\x64ress\x18\x01 \x01(\t\"\x1d\n\nIP6Address\x12\x0f\n\x07\x61\x64\x64ress\x18\x01 \x01(\t\"\x98\x01\n\nScanConfig\x12\x0c\n\x04ssid\x18\x01 \x03(\x0c\x12\r\n\x05\x62ssid\x18\x02 \x03(\x0c\x12\x0f\n\x07\x63hannel\x18\x03 \x01(\r\x12\x13\n\x0bshow_hidden\x18\x04 \x01(\x08\x12\x13\n\x0b\x61\x63tive_scan\x18\x05 \x01(\x08\x12\x18\n\x10scan_time_min_ms\x18\x06 \x01(\r\x12\x18\n\x10scan_time_max_ms\x18\x07 \x01(\r\"\x92\x01\n\nScanResult\x12\x0c\n\x04ssid\x18\x01 \x01(\x0c\x12\r\n\x05\x62ssid\x18\x02 \x01(\x0c\x12\x33\n\rsecurity_type\x18\x03 \x01(\x0e\x32\x1c.chip.rpc.WIFI_SECURITY_TYPE\x12\x11\n\tfrequency\x18\x04 \x01(\r\x12\x0f\n\x07\x63hannel\x18\x05 \x01(\r\x12\x0e\n\x06signal\x18\x06 \x01(\x05\"0\n\x0bScanResults\x12!\n\x03\x61ps\x18\x01 \x03(\x0b\x32\x14.chip.rpc.ScanResult\"c\n\x0e\x43onnectionData\x12\x0c\n\x04ssid\x18\x01 \x01(\x0c\x12\x33\n\rsecurity_type\x18\x02 \x01(\x0e\x32\x1c.chip.rpc.WIFI_SECURITY_TYPE\x12\x0e\n\x06secret\x18\x03 \x01(\x0c\"=\n\x10\x43onnectionResult\x12)\n\x05\x65rror\x18\x01 \x01(\x0e\x32\x1a.chip.rpc.CONNECTION_ERROR*\xf2\x01\n\x12WIFI_SECURITY_TYPE\x12\x12\n\x0eWIFI_AUTH_OPEN\x10\x00\x12\x11\n\rWIFI_AUTH_WEP\x10\x01\x12\x15\n\x11WIFI_AUTH_WPA_PSK\x10\x02\x12\x16\n\x12WIFI_AUTH_WPA2_PSK\x10\x03\x12\x1a\n\x16WIFI_AUTH_WPA_WPA2_PSK\x10\x04\x12\x1d\n\x19WIFI_AUTH_WPA2_ENTERPRISE\x10\x05\x12\x16\n\x12WIFI_AUTH_WPA3_PSK\x10\x06\x12\x1b\n\x17WIFI_AUTH_WPA2_WPA3_PSK\x10\x07\x12\x16\n\x12WIFI_AUTH_WAPI_PSK\x10\x08*\xbf\x05\n\x10\x43ONNECTION_ERROR\x12\x06\n\x02OK\x10\x00\x12\x0f\n\x0bUNSPECIFIED\x10\x01\x12\x0f\n\x0b\x41UTH_EXPIRE\x10\x02\x12\x0e\n\nAUTH_LEAVE\x10\x03\x12\x10\n\x0c\x41SSOC_EXPIRE\x10\x04\x12\x11\n\rASSOC_TOOMANY\x10\x05\x12\x0e\n\nNOT_AUTHED\x10\x06\x12\x0f\n\x0bNOT_ASSOCED\x10\x07\x12\x0f\n\x0b\x41SSOC_LEAVE\x10\x08\x12\x14\n\x10\x41SSOC_NOT_AUTHED\x10\t\x12\x17\n\x13\x44ISASSOC_PWRCAP_BAD\x10\n\x12\x18\n\x14\x44ISASSOC_SUPCHAN_BAD\x10\x0b\x12\x0e\n\nIE_INVALID\x10\r\x12\x0f\n\x0bMIC_FAILURE\x10\x0e\x12\x1d\n\x19\x46OURWAY_HANDSHAKE_TIMEOUT\x10\x0f\x12\x1c\n\x18GROUP_KEY_UPDATE_TIMEOUT\x10\x10\x12\x16\n\x12IE_IN_4WAY_DIFFERS\x10\x11\x12\x18\n\x14GROUP_CIPHER_INVALID\x10\x12\x12\x1b\n\x17PAIRWISE_CIPHER_INVALID\x10\x13\x12\x10\n\x0c\x41KMP_INVALID\x10\x14\x12\x19\n\x15UNSUPP_RSN_IE_VERSION\x10\x15\x12\x16\n\x12INVALID_RSN_IE_CAP\x10\x16\x12\x1a\n\x16IEEE802_1X_AUTH_FAILED\x10\x17\x12\x19\n\x15\x43IPHER_SUITE_REJECTED\x10\x18\x12\x11\n\rINVALID_PMKID\x10\x35\x12\x13\n\x0e\x42\x45\x41\x43ON_TIMEOUT\x10\xc8\x01\x12\x10\n\x0bNO_AP_FOUND\x10\xc9\x01\x12\x0e\n\tAUTH_FAIL\x10\xca\x01\x12\x0f\n\nASSOC_FAIL\x10\xcb\x01\x12\x16\n\x11HANDSHAKE_TIMEOUT\x10\xcc\x01\x12\x14\n\x0f\x43ONNECTION_FAIL\x10\xcd\x01\x12\x11\n\x0c\x41P_TSF_RESET\x10\xce\x01\x12\x0c\n\x07ROAMING\x10\xcf\x01\x32\x8a\x05\n\x04WiFi\x12\x35\n\nGetChannel\x12\x12.pw.protobuf.Empty\x1a\x11.chip.rpc.Channel\"\x00\x12/\n\x07GetSsid\x12\x12.pw.protobuf.Empty\x1a\x0e.chip.rpc.Ssid\"\x00\x12\x31\n\x08GetState\x12\x12.pw.protobuf.Empty\x1a\x0f.chip.rpc.State\"\x00\x12;\n\rGetMacAddress\x12\x12.pw.protobuf.Empty\x1a\x14.chip.rpc.MacAddress\"\x00\x12\x41\n\x10GetWiFiInterface\x12\x12.pw.protobuf.Empty\x1a\x17.chip.rpc.WiFiInterface\"\x00\x12;\n\rGetIP4Address\x12\x12.pw.protobuf.Empty\x1a\x14.chip.rpc.IP4Address\"\x00\x12;\n\rGetIP6Address\x12\x12.pw.protobuf.Empty\x1a\x14.chip.rpc.IP6Address\"\x00\x12<\n\tStartScan\x12\x14.chip.rpc.ScanConfig\x1a\x15.chip.rpc.ScanResults\"\x00\x30\x01\x12\x34\n\x08StopScan\x12\x12.pw.protobuf.Empty\x1a\x12.pw.protobuf.Empty\"\x00\x12\x41\n\x07\x43onnect\x12\x18.chip.rpc.ConnectionData\x1a\x1a.chip.rpc.ConnectionResult\"\x00\x12\x36\n\nDisconnect\x12\x12.pw.protobuf.Empty\x1a\x12.pw.protobuf.Empty\"\x00\x62\x06proto3'
  ,
  dependencies=[common__pb2.DESCRIPTOR,])

_WIFI_SECURITY_TYPE = _descriptor.EnumDescriptor(
  name='WIFI_SECURITY_TYPE',
  full_name='chip.rpc.WIFI_SECURITY_TYPE',
  filename=None,
  file=DESCRIPTOR,
  create_key=_descriptor._internal_create_key,
  values=[
    _descriptor.EnumValueDescriptor(
      name='WIFI_AUTH_OPEN', index=0, number=0,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='WIFI_AUTH_WEP', index=1, number=1,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='WIFI_AUTH_WPA_PSK', index=2, number=2,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='WIFI_AUTH_WPA2_PSK', index=3, number=3,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='WIFI_AUTH_WPA_WPA2_PSK', index=4, number=4,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='WIFI_AUTH_WPA2_ENTERPRISE', index=5, number=5,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='WIFI_AUTH_WPA3_PSK', index=6, number=6,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='WIFI_AUTH_WPA2_WPA3_PSK', index=7, number=7,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='WIFI_AUTH_WAPI_PSK', index=8, number=8,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=776,
  serialized_end=1018,
)
_sym_db.RegisterEnumDescriptor(_WIFI_SECURITY_TYPE)

WIFI_SECURITY_TYPE = enum_type_wrapper.EnumTypeWrapper(_WIFI_SECURITY_TYPE)
_CONNECTION_ERROR = _descriptor.EnumDescriptor(
  name='CONNECTION_ERROR',
  full_name='chip.rpc.CONNECTION_ERROR',
  filename=None,
  file=DESCRIPTOR,
  create_key=_descriptor._internal_create_key,
  values=[
    _descriptor.EnumValueDescriptor(
      name='OK', index=0, number=0,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='UNSPECIFIED', index=1, number=1,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='AUTH_EXPIRE', index=2, number=2,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='AUTH_LEAVE', index=3, number=3,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ASSOC_EXPIRE', index=4, number=4,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ASSOC_TOOMANY', index=5, number=5,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='NOT_AUTHED', index=6, number=6,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='NOT_ASSOCED', index=7, number=7,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ASSOC_LEAVE', index=8, number=8,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ASSOC_NOT_AUTHED', index=9, number=9,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='DISASSOC_PWRCAP_BAD', index=10, number=10,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='DISASSOC_SUPCHAN_BAD', index=11, number=11,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='IE_INVALID', index=12, number=13,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='MIC_FAILURE', index=13, number=14,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='FOURWAY_HANDSHAKE_TIMEOUT', index=14, number=15,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='GROUP_KEY_UPDATE_TIMEOUT', index=15, number=16,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='IE_IN_4WAY_DIFFERS', index=16, number=17,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='GROUP_CIPHER_INVALID', index=17, number=18,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='PAIRWISE_CIPHER_INVALID', index=18, number=19,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='AKMP_INVALID', index=19, number=20,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='UNSUPP_RSN_IE_VERSION', index=20, number=21,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='INVALID_RSN_IE_CAP', index=21, number=22,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='IEEE802_1X_AUTH_FAILED', index=22, number=23,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='CIPHER_SUITE_REJECTED', index=23, number=24,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='INVALID_PMKID', index=24, number=53,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='BEACON_TIMEOUT', index=25, number=200,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='NO_AP_FOUND', index=26, number=201,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='AUTH_FAIL', index=27, number=202,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ASSOC_FAIL', index=28, number=203,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='HANDSHAKE_TIMEOUT', index=29, number=204,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='CONNECTION_FAIL', index=30, number=205,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='AP_TSF_RESET', index=31, number=206,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ROAMING', index=32, number=207,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=1021,
  serialized_end=1724,
)
_sym_db.RegisterEnumDescriptor(_CONNECTION_ERROR)

CONNECTION_ERROR = enum_type_wrapper.EnumTypeWrapper(_CONNECTION_ERROR)
WIFI_AUTH_OPEN = 0
WIFI_AUTH_WEP = 1
WIFI_AUTH_WPA_PSK = 2
WIFI_AUTH_WPA2_PSK = 3
WIFI_AUTH_WPA_WPA2_PSK = 4
WIFI_AUTH_WPA2_ENTERPRISE = 5
WIFI_AUTH_WPA3_PSK = 6
WIFI_AUTH_WPA2_WPA3_PSK = 7
WIFI_AUTH_WAPI_PSK = 8
OK = 0
UNSPECIFIED = 1
AUTH_EXPIRE = 2
AUTH_LEAVE = 3
ASSOC_EXPIRE = 4
ASSOC_TOOMANY = 5
NOT_AUTHED = 6
NOT_ASSOCED = 7
ASSOC_LEAVE = 8
ASSOC_NOT_AUTHED = 9
DISASSOC_PWRCAP_BAD = 10
DISASSOC_SUPCHAN_BAD = 11
IE_INVALID = 13
MIC_FAILURE = 14
FOURWAY_HANDSHAKE_TIMEOUT = 15
GROUP_KEY_UPDATE_TIMEOUT = 16
IE_IN_4WAY_DIFFERS = 17
GROUP_CIPHER_INVALID = 18
PAIRWISE_CIPHER_INVALID = 19
AKMP_INVALID = 20
UNSUPP_RSN_IE_VERSION = 21
INVALID_RSN_IE_CAP = 22
IEEE802_1X_AUTH_FAILED = 23
CIPHER_SUITE_REJECTED = 24
INVALID_PMKID = 53
BEACON_TIMEOUT = 200
NO_AP_FOUND = 201
AUTH_FAIL = 202
ASSOC_FAIL = 203
HANDSHAKE_TIMEOUT = 204
CONNECTION_FAIL = 205
AP_TSF_RESET = 206
ROAMING = 207



_CHANNEL = _descriptor.Descriptor(
  name='Channel',
  full_name='chip.rpc.Channel',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='channel', full_name='chip.rpc.Channel.channel', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=46,
  serialized_end=72,
)


_SSID = _descriptor.Descriptor(
  name='Ssid',
  full_name='chip.rpc.Ssid',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='ssid', full_name='chip.rpc.Ssid.ssid', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=b"",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=74,
  serialized_end=94,
)


_STATE = _descriptor.Descriptor(
  name='State',
  full_name='chip.rpc.State',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='connected', full_name='chip.rpc.State.connected', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=96,
  serialized_end=122,
)


_MACADDRESS = _descriptor.Descriptor(
  name='MacAddress',
  full_name='chip.rpc.MacAddress',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='mac_address', full_name='chip.rpc.MacAddress.mac_address', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=124,
  serialized_end=157,
)


_WIFIINTERFACE = _descriptor.Descriptor(
  name='WiFiInterface',
  full_name='chip.rpc.WiFiInterface',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='interface', full_name='chip.rpc.WiFiInterface.interface', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=159,
  serialized_end=193,
)


_IP4ADDRESS = _descriptor.Descriptor(
  name='IP4Address',
  full_name='chip.rpc.IP4Address',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='address', full_name='chip.rpc.IP4Address.address', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=195,
  serialized_end=224,
)


_IP6ADDRESS = _descriptor.Descriptor(
  name='IP6Address',
  full_name='chip.rpc.IP6Address',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='address', full_name='chip.rpc.IP6Address.address', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=226,
  serialized_end=255,
)


_SCANCONFIG = _descriptor.Descriptor(
  name='ScanConfig',
  full_name='chip.rpc.ScanConfig',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='ssid', full_name='chip.rpc.ScanConfig.ssid', index=0,
      number=1, type=12, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='bssid', full_name='chip.rpc.ScanConfig.bssid', index=1,
      number=2, type=12, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='channel', full_name='chip.rpc.ScanConfig.channel', index=2,
      number=3, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='show_hidden', full_name='chip.rpc.ScanConfig.show_hidden', index=3,
      number=4, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='active_scan', full_name='chip.rpc.ScanConfig.active_scan', index=4,
      number=5, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='scan_time_min_ms', full_name='chip.rpc.ScanConfig.scan_time_min_ms', index=5,
      number=6, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='scan_time_max_ms', full_name='chip.rpc.ScanConfig.scan_time_max_ms', index=6,
      number=7, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=258,
  serialized_end=410,
)


_SCANRESULT = _descriptor.Descriptor(
  name='ScanResult',
  full_name='chip.rpc.ScanResult',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='ssid', full_name='chip.rpc.ScanResult.ssid', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=b"",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='bssid', full_name='chip.rpc.ScanResult.bssid', index=1,
      number=2, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=b"",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='security_type', full_name='chip.rpc.ScanResult.security_type', index=2,
      number=3, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='frequency', full_name='chip.rpc.ScanResult.frequency', index=3,
      number=4, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='channel', full_name='chip.rpc.ScanResult.channel', index=4,
      number=5, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='signal', full_name='chip.rpc.ScanResult.signal', index=5,
      number=6, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=413,
  serialized_end=559,
)


_SCANRESULTS = _descriptor.Descriptor(
  name='ScanResults',
  full_name='chip.rpc.ScanResults',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='aps', full_name='chip.rpc.ScanResults.aps', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=561,
  serialized_end=609,
)


_CONNECTIONDATA = _descriptor.Descriptor(
  name='ConnectionData',
  full_name='chip.rpc.ConnectionData',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='ssid', full_name='chip.rpc.ConnectionData.ssid', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=b"",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='security_type', full_name='chip.rpc.ConnectionData.security_type', index=1,
      number=2, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='secret', full_name='chip.rpc.ConnectionData.secret', index=2,
      number=3, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=b"",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=611,
  serialized_end=710,
)


_CONNECTIONRESULT = _descriptor.Descriptor(
  name='ConnectionResult',
  full_name='chip.rpc.ConnectionResult',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='error', full_name='chip.rpc.ConnectionResult.error', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=712,
  serialized_end=773,
)

_SCANRESULT.fields_by_name['security_type'].enum_type = _WIFI_SECURITY_TYPE
_SCANRESULTS.fields_by_name['aps'].message_type = _SCANRESULT
_CONNECTIONDATA.fields_by_name['security_type'].enum_type = _WIFI_SECURITY_TYPE
_CONNECTIONRESULT.fields_by_name['error'].enum_type = _CONNECTION_ERROR
DESCRIPTOR.message_types_by_name['Channel'] = _CHANNEL
DESCRIPTOR.message_types_by_name['Ssid'] = _SSID
DESCRIPTOR.message_types_by_name['State'] = _STATE
DESCRIPTOR.message_types_by_name['MacAddress'] = _MACADDRESS
DESCRIPTOR.message_types_by_name['WiFiInterface'] = _WIFIINTERFACE
DESCRIPTOR.message_types_by_name['IP4Address'] = _IP4ADDRESS
DESCRIPTOR.message_types_by_name['IP6Address'] = _IP6ADDRESS
DESCRIPTOR.message_types_by_name['ScanConfig'] = _SCANCONFIG
DESCRIPTOR.message_types_by_name['ScanResult'] = _SCANRESULT
DESCRIPTOR.message_types_by_name['ScanResults'] = _SCANRESULTS
DESCRIPTOR.message_types_by_name['ConnectionData'] = _CONNECTIONDATA
DESCRIPTOR.message_types_by_name['ConnectionResult'] = _CONNECTIONRESULT
DESCRIPTOR.enum_types_by_name['WIFI_SECURITY_TYPE'] = _WIFI_SECURITY_TYPE
DESCRIPTOR.enum_types_by_name['CONNECTION_ERROR'] = _CONNECTION_ERROR
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

Channel = _reflection.GeneratedProtocolMessageType('Channel', (_message.Message,), {
  'DESCRIPTOR' : _CHANNEL,
  '__module__' : 'wifi_service_pb2'
  # @@protoc_insertion_point(class_scope:chip.rpc.Channel)
  })
_sym_db.RegisterMessage(Channel)

Ssid = _reflection.GeneratedProtocolMessageType('Ssid', (_message.Message,), {
  'DESCRIPTOR' : _SSID,
  '__module__' : 'wifi_service_pb2'
  # @@protoc_insertion_point(class_scope:chip.rpc.Ssid)
  })
_sym_db.RegisterMessage(Ssid)

State = _reflection.GeneratedProtocolMessageType('State', (_message.Message,), {
  'DESCRIPTOR' : _STATE,
  '__module__' : 'wifi_service_pb2'
  # @@protoc_insertion_point(class_scope:chip.rpc.State)
  })
_sym_db.RegisterMessage(State)

MacAddress = _reflection.GeneratedProtocolMessageType('MacAddress', (_message.Message,), {
  'DESCRIPTOR' : _MACADDRESS,
  '__module__' : 'wifi_service_pb2'
  # @@protoc_insertion_point(class_scope:chip.rpc.MacAddress)
  })
_sym_db.RegisterMessage(MacAddress)

WiFiInterface = _reflection.GeneratedProtocolMessageType('WiFiInterface', (_message.Message,), {
  'DESCRIPTOR' : _WIFIINTERFACE,
  '__module__' : 'wifi_service_pb2'
  # @@protoc_insertion_point(class_scope:chip.rpc.WiFiInterface)
  })
_sym_db.RegisterMessage(WiFiInterface)

IP4Address = _reflection.GeneratedProtocolMessageType('IP4Address', (_message.Message,), {
  'DESCRIPTOR' : _IP4ADDRESS,
  '__module__' : 'wifi_service_pb2'
  # @@protoc_insertion_point(class_scope:chip.rpc.IP4Address)
  })
_sym_db.RegisterMessage(IP4Address)

IP6Address = _reflection.GeneratedProtocolMessageType('IP6Address', (_message.Message,), {
  'DESCRIPTOR' : _IP6ADDRESS,
  '__module__' : 'wifi_service_pb2'
  # @@protoc_insertion_point(class_scope:chip.rpc.IP6Address)
  })
_sym_db.RegisterMessage(IP6Address)

ScanConfig = _reflection.GeneratedProtocolMessageType('ScanConfig', (_message.Message,), {
  'DESCRIPTOR' : _SCANCONFIG,
  '__module__' : 'wifi_service_pb2'
  # @@protoc_insertion_point(class_scope:chip.rpc.ScanConfig)
  })
_sym_db.RegisterMessage(ScanConfig)

ScanResult = _reflection.GeneratedProtocolMessageType('ScanResult', (_message.Message,), {
  'DESCRIPTOR' : _SCANRESULT,
  '__module__' : 'wifi_service_pb2'
  # @@protoc_insertion_point(class_scope:chip.rpc.ScanResult)
  })
_sym_db.RegisterMessage(ScanResult)

ScanResults = _reflection.GeneratedProtocolMessageType('ScanResults', (_message.Message,), {
  'DESCRIPTOR' : _SCANRESULTS,
  '__module__' : 'wifi_service_pb2'
  # @@protoc_insertion_point(class_scope:chip.rpc.ScanResults)
  })
_sym_db.RegisterMessage(ScanResults)

ConnectionData = _reflection.GeneratedProtocolMessageType('ConnectionData', (_message.Message,), {
  'DESCRIPTOR' : _CONNECTIONDATA,
  '__module__' : 'wifi_service_pb2'
  # @@protoc_insertion_point(class_scope:chip.rpc.ConnectionData)
  })
_sym_db.RegisterMessage(ConnectionData)

ConnectionResult = _reflection.GeneratedProtocolMessageType('ConnectionResult', (_message.Message,), {
  'DESCRIPTOR' : _CONNECTIONRESULT,
  '__module__' : 'wifi_service_pb2'
  # @@protoc_insertion_point(class_scope:chip.rpc.ConnectionResult)
  })
_sym_db.RegisterMessage(ConnectionResult)



_WIFI = _descriptor.ServiceDescriptor(
  name='WiFi',
  full_name='chip.rpc.WiFi',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_start=1727,
  serialized_end=2377,
  methods=[
  _descriptor.MethodDescriptor(
    name='GetChannel',
    full_name='chip.rpc.WiFi.GetChannel',
    index=0,
    containing_service=None,
    input_type=common__pb2._EMPTY,
    output_type=_CHANNEL,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
  _descriptor.MethodDescriptor(
    name='GetSsid',
    full_name='chip.rpc.WiFi.GetSsid',
    index=1,
    containing_service=None,
    input_type=common__pb2._EMPTY,
    output_type=_SSID,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
  _descriptor.MethodDescriptor(
    name='GetState',
    full_name='chip.rpc.WiFi.GetState',
    index=2,
    containing_service=None,
    input_type=common__pb2._EMPTY,
    output_type=_STATE,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
  _descriptor.MethodDescriptor(
    name='GetMacAddress',
    full_name='chip.rpc.WiFi.GetMacAddress',
    index=3,
    containing_service=None,
    input_type=common__pb2._EMPTY,
    output_type=_MACADDRESS,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
  _descriptor.MethodDescriptor(
    name='GetWiFiInterface',
    full_name='chip.rpc.WiFi.GetWiFiInterface',
    index=4,
    containing_service=None,
    input_type=common__pb2._EMPTY,
    output_type=_WIFIINTERFACE,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
  _descriptor.MethodDescriptor(
    name='GetIP4Address',
    full_name='chip.rpc.WiFi.GetIP4Address',
    index=5,
    containing_service=None,
    input_type=common__pb2._EMPTY,
    output_type=_IP4ADDRESS,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
  _descriptor.MethodDescriptor(
    name='GetIP6Address',
    full_name='chip.rpc.WiFi.GetIP6Address',
    index=6,
    containing_service=None,
    input_type=common__pb2._EMPTY,
    output_type=_IP6ADDRESS,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
  _descriptor.MethodDescriptor(
    name='StartScan',
    full_name='chip.rpc.WiFi.StartScan',
    index=7,
    containing_service=None,
    input_type=_SCANCONFIG,
    output_type=_SCANRESULTS,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
  _descriptor.MethodDescriptor(
    name='StopScan',
    full_name='chip.rpc.WiFi.StopScan',
    index=8,
    containing_service=None,
    input_type=common__pb2._EMPTY,
    output_type=common__pb2._EMPTY,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
  _descriptor.MethodDescriptor(
    name='Connect',
    full_name='chip.rpc.WiFi.Connect',
    index=9,
    containing_service=None,
    input_type=_CONNECTIONDATA,
    output_type=_CONNECTIONRESULT,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
  _descriptor.MethodDescriptor(
    name='Disconnect',
    full_name='chip.rpc.WiFi.Disconnect',
    index=10,
    containing_service=None,
    input_type=common__pb2._EMPTY,
    output_type=common__pb2._EMPTY,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
])
_sym_db.RegisterServiceDescriptor(_WIFI)

DESCRIPTOR.services_by_name['WiFi'] = _WIFI

# @@protoc_insertion_point(module_scope)
