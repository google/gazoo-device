# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: attributes_service.proto
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
  name='attributes_service.proto',
  package='chip.rpc',
  syntax='proto3',
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_pb=b'\n\x18\x61ttributes_service.proto\x12\x08\x63hip.rpc\x1a\x0c\x63ommon.proto\"s\n\x11\x41ttributeMetadata\x12\x10\n\x08\x65ndpoint\x18\x01 \x01(\r\x12\x0f\n\x07\x63luster\x18\x02 \x01(\r\x12\x14\n\x0c\x61ttribute_id\x18\x03 \x01(\r\x12%\n\x04type\x18\x04 \x01(\x0e\x32\x17.chip.rpc.AttributeType\"\x86\x01\n\rAttributeData\x12\x13\n\tdata_bool\x18\x01 \x01(\x08H\x00\x12\x14\n\ndata_uint8\x18\x02 \x01(\rH\x00\x12\x15\n\x0b\x64\x61ta_uint16\x18\x03 \x01(\rH\x00\x12\x15\n\x0b\x64\x61ta_uint32\x18\x04 \x01(\rH\x00\x12\x14\n\ndata_bytes\x18\x05 \x01(\x0cH\x00\x42\x06\n\x04\x64\x61ta\"f\n\x0e\x41ttributeWrite\x12-\n\x08metadata\x18\x01 \x01(\x0b\x32\x1b.chip.rpc.AttributeMetadata\x12%\n\x04\x64\x61ta\x18\x02 \x01(\x0b\x32\x17.chip.rpc.AttributeData*\xab\x10\n\rAttributeType\x12\x1e\n\x1aZCL_NO_DATA_ATTRIBUTE_TYPE\x10\x00\x12\x1e\n\x1aZCL_BOOLEAN_ATTRIBUTE_TYPE\x10\x10\x12\x1e\n\x1aZCL_BITMAP8_ATTRIBUTE_TYPE\x10\x18\x12\x1f\n\x1bZCL_BITMAP16_ATTRIBUTE_TYPE\x10\x19\x12\x1f\n\x1bZCL_BITMAP32_ATTRIBUTE_TYPE\x10\x1b\x12\x1f\n\x1bZCL_BITMAP64_ATTRIBUTE_TYPE\x10\x1f\x12\x1c\n\x18ZCL_INT8U_ATTRIBUTE_TYPE\x10 \x12\x1d\n\x19ZCL_INT16U_ATTRIBUTE_TYPE\x10!\x12\x1d\n\x19ZCL_INT24U_ATTRIBUTE_TYPE\x10\"\x12\x1d\n\x19ZCL_INT32U_ATTRIBUTE_TYPE\x10#\x12\x1d\n\x19ZCL_INT40U_ATTRIBUTE_TYPE\x10$\x12\x1d\n\x19ZCL_INT48U_ATTRIBUTE_TYPE\x10%\x12\x1d\n\x19ZCL_INT56U_ATTRIBUTE_TYPE\x10&\x12\x1d\n\x19ZCL_INT64U_ATTRIBUTE_TYPE\x10\'\x12\x1c\n\x18ZCL_INT8S_ATTRIBUTE_TYPE\x10(\x12\x1d\n\x19ZCL_INT16S_ATTRIBUTE_TYPE\x10)\x12\x1d\n\x19ZCL_INT24S_ATTRIBUTE_TYPE\x10*\x12\x1d\n\x19ZCL_INT32S_ATTRIBUTE_TYPE\x10+\x12\x1d\n\x19ZCL_INT40S_ATTRIBUTE_TYPE\x10,\x12\x1d\n\x19ZCL_INT48S_ATTRIBUTE_TYPE\x10-\x12\x1d\n\x19ZCL_INT56S_ATTRIBUTE_TYPE\x10.\x12\x1d\n\x19ZCL_INT64S_ATTRIBUTE_TYPE\x10/\x12\x1c\n\x18ZCL_ENUM8_ATTRIBUTE_TYPE\x10\x30\x12\x1d\n\x19ZCL_ENUM16_ATTRIBUTE_TYPE\x10\x31\x12\x1d\n\x19ZCL_SINGLE_ATTRIBUTE_TYPE\x10\x39\x12\x1d\n\x19ZCL_DOUBLE_ATTRIBUTE_TYPE\x10:\x12#\n\x1fZCL_OCTET_STRING_ATTRIBUTE_TYPE\x10\x41\x12\"\n\x1eZCL_CHAR_STRING_ATTRIBUTE_TYPE\x10\x42\x12(\n$ZCL_LONG_OCTET_STRING_ATTRIBUTE_TYPE\x10\x43\x12\'\n#ZCL_LONG_CHAR_STRING_ATTRIBUTE_TYPE\x10\x44\x12\x1c\n\x18ZCL_ARRAY_ATTRIBUTE_TYPE\x10H\x12\x1d\n\x19ZCL_STRUCT_ATTRIBUTE_TYPE\x10L\x12\x1b\n\x16ZCL_TOD_ATTRIBUTE_TYPE\x10\xe0\x01\x12\x1c\n\x17ZCL_DATE_ATTRIBUTE_TYPE\x10\xe1\x01\x12\x1b\n\x16ZCL_UTC_ATTRIBUTE_TYPE\x10\xe2\x01\x12 \n\x1bZCL_EPOCH_US_ATTRIBUTE_TYPE\x10\xe3\x01\x12\x1f\n\x1aZCL_EPOCH_S_ATTRIBUTE_TYPE\x10\xe4\x01\x12\"\n\x1dZCL_SYSTIME_US_ATTRIBUTE_TYPE\x10\xe5\x01\x12\x1f\n\x1aZCL_PERCENT_ATTRIBUTE_TYPE\x10\xe6\x01\x12%\n ZCL_PERCENT100THS_ATTRIBUTE_TYPE\x10\xe7\x01\x12\"\n\x1dZCL_CLUSTER_ID_ATTRIBUTE_TYPE\x10\xe8\x01\x12!\n\x1cZCL_ATTRIB_ID_ATTRIBUTE_TYPE\x10\xe9\x01\x12 \n\x1bZCL_FIELD_ID_ATTRIBUTE_TYPE\x10\xea\x01\x12 \n\x1bZCL_EVENT_ID_ATTRIBUTE_TYPE\x10\xeb\x01\x12\"\n\x1dZCL_COMMAND_ID_ATTRIBUTE_TYPE\x10\xec\x01\x12!\n\x1cZCL_ACTION_ID_ATTRIBUTE_TYPE\x10\xed\x01\x12 \n\x1bZCL_TRANS_ID_ATTRIBUTE_TYPE\x10\xef\x01\x12\x1f\n\x1aZCL_NODE_ID_ATTRIBUTE_TYPE\x10\xf0\x01\x12!\n\x1cZCL_VENDOR_ID_ATTRIBUTE_TYPE\x10\xf1\x01\x12\"\n\x1dZCL_DEVTYPE_ID_ATTRIBUTE_TYPE\x10\xf2\x01\x12!\n\x1cZCL_FABRIC_ID_ATTRIBUTE_TYPE\x10\xf3\x01\x12 \n\x1bZCL_GROUP_ID_ATTRIBUTE_TYPE\x10\xf4\x01\x12\x1e\n\x19ZCL_STATUS_ATTRIBUTE_TYPE\x10\xf5\x01\x12 \n\x1bZCL_DATA_VER_ATTRIBUTE_TYPE\x10\xf6\x01\x12 \n\x1bZCL_EVENT_NO_ATTRIBUTE_TYPE\x10\xf7\x01\x12#\n\x1eZCL_ENDPOINT_NO_ATTRIBUTE_TYPE\x10\xf8\x01\x12\"\n\x1dZCL_FABRIC_IDX_ATTRIBUTE_TYPE\x10\xf9\x01\x12\x1d\n\x18ZCL_IPADR_ATTRIBUTE_TYPE\x10\xfa\x01\x12\x1f\n\x1aZCL_IPV4ADR_ATTRIBUTE_TYPE\x10\xfb\x01\x12\x1f\n\x1aZCL_IPV6ADR_ATTRIBUTE_TYPE\x10\xfc\x01\x12\x1f\n\x1aZCL_IPV6PRE_ATTRIBUTE_TYPE\x10\xfd\x01\x12\x1d\n\x18ZCL_HWADR_ATTRIBUTE_TYPE\x10\xfe\x01\x12\x1f\n\x1aZCL_UNKNOWN_ATTRIBUTE_TYPE\x10\xff\x01\x32\x85\x01\n\nAttributes\x12\x37\n\x05Write\x12\x18.chip.rpc.AttributeWrite\x1a\x12.pw.protobuf.Empty\"\x00\x12>\n\x04Read\x12\x1b.chip.rpc.AttributeMetadata\x1a\x17.chip.rpc.AttributeData\"\x00\x62\x06proto3'
  ,
  dependencies=[common__pb2.DESCRIPTOR,])

_ATTRIBUTETYPE = _descriptor.EnumDescriptor(
  name='AttributeType',
  full_name='chip.rpc.AttributeType',
  filename=None,
  file=DESCRIPTOR,
  create_key=_descriptor._internal_create_key,
  values=[
    _descriptor.EnumValueDescriptor(
      name='ZCL_NO_DATA_ATTRIBUTE_TYPE', index=0, number=0,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_BOOLEAN_ATTRIBUTE_TYPE', index=1, number=16,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_BITMAP8_ATTRIBUTE_TYPE', index=2, number=24,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_BITMAP16_ATTRIBUTE_TYPE', index=3, number=25,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_BITMAP32_ATTRIBUTE_TYPE', index=4, number=27,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_BITMAP64_ATTRIBUTE_TYPE', index=5, number=31,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_INT8U_ATTRIBUTE_TYPE', index=6, number=32,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_INT16U_ATTRIBUTE_TYPE', index=7, number=33,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_INT24U_ATTRIBUTE_TYPE', index=8, number=34,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_INT32U_ATTRIBUTE_TYPE', index=9, number=35,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_INT40U_ATTRIBUTE_TYPE', index=10, number=36,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_INT48U_ATTRIBUTE_TYPE', index=11, number=37,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_INT56U_ATTRIBUTE_TYPE', index=12, number=38,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_INT64U_ATTRIBUTE_TYPE', index=13, number=39,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_INT8S_ATTRIBUTE_TYPE', index=14, number=40,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_INT16S_ATTRIBUTE_TYPE', index=15, number=41,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_INT24S_ATTRIBUTE_TYPE', index=16, number=42,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_INT32S_ATTRIBUTE_TYPE', index=17, number=43,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_INT40S_ATTRIBUTE_TYPE', index=18, number=44,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_INT48S_ATTRIBUTE_TYPE', index=19, number=45,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_INT56S_ATTRIBUTE_TYPE', index=20, number=46,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_INT64S_ATTRIBUTE_TYPE', index=21, number=47,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_ENUM8_ATTRIBUTE_TYPE', index=22, number=48,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_ENUM16_ATTRIBUTE_TYPE', index=23, number=49,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_SINGLE_ATTRIBUTE_TYPE', index=24, number=57,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_DOUBLE_ATTRIBUTE_TYPE', index=25, number=58,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_OCTET_STRING_ATTRIBUTE_TYPE', index=26, number=65,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_CHAR_STRING_ATTRIBUTE_TYPE', index=27, number=66,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_LONG_OCTET_STRING_ATTRIBUTE_TYPE', index=28, number=67,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_LONG_CHAR_STRING_ATTRIBUTE_TYPE', index=29, number=68,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_ARRAY_ATTRIBUTE_TYPE', index=30, number=72,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_STRUCT_ATTRIBUTE_TYPE', index=31, number=76,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_TOD_ATTRIBUTE_TYPE', index=32, number=224,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_DATE_ATTRIBUTE_TYPE', index=33, number=225,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_UTC_ATTRIBUTE_TYPE', index=34, number=226,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_EPOCH_US_ATTRIBUTE_TYPE', index=35, number=227,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_EPOCH_S_ATTRIBUTE_TYPE', index=36, number=228,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_SYSTIME_US_ATTRIBUTE_TYPE', index=37, number=229,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_PERCENT_ATTRIBUTE_TYPE', index=38, number=230,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_PERCENT100THS_ATTRIBUTE_TYPE', index=39, number=231,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_CLUSTER_ID_ATTRIBUTE_TYPE', index=40, number=232,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_ATTRIB_ID_ATTRIBUTE_TYPE', index=41, number=233,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_FIELD_ID_ATTRIBUTE_TYPE', index=42, number=234,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_EVENT_ID_ATTRIBUTE_TYPE', index=43, number=235,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_COMMAND_ID_ATTRIBUTE_TYPE', index=44, number=236,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_ACTION_ID_ATTRIBUTE_TYPE', index=45, number=237,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_TRANS_ID_ATTRIBUTE_TYPE', index=46, number=239,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_NODE_ID_ATTRIBUTE_TYPE', index=47, number=240,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_VENDOR_ID_ATTRIBUTE_TYPE', index=48, number=241,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_DEVTYPE_ID_ATTRIBUTE_TYPE', index=49, number=242,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_FABRIC_ID_ATTRIBUTE_TYPE', index=50, number=243,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_GROUP_ID_ATTRIBUTE_TYPE', index=51, number=244,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_STATUS_ATTRIBUTE_TYPE', index=52, number=245,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_DATA_VER_ATTRIBUTE_TYPE', index=53, number=246,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_EVENT_NO_ATTRIBUTE_TYPE', index=54, number=247,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_ENDPOINT_NO_ATTRIBUTE_TYPE', index=55, number=248,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_FABRIC_IDX_ATTRIBUTE_TYPE', index=56, number=249,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_IPADR_ATTRIBUTE_TYPE', index=57, number=250,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_IPV4ADR_ATTRIBUTE_TYPE', index=58, number=251,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_IPV6ADR_ATTRIBUTE_TYPE', index=59, number=252,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_IPV6PRE_ATTRIBUTE_TYPE', index=60, number=253,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_HWADR_ATTRIBUTE_TYPE', index=61, number=254,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
    _descriptor.EnumValueDescriptor(
      name='ZCL_UNKNOWN_ATTRIBUTE_TYPE', index=62, number=255,
      serialized_options=None,
      type=None,
      create_key=_descriptor._internal_create_key),
  ],
  containing_type=None,
  serialized_options=None,
  serialized_start=411,
  serialized_end=2502,
)
_sym_db.RegisterEnumDescriptor(_ATTRIBUTETYPE)

AttributeType = enum_type_wrapper.EnumTypeWrapper(_ATTRIBUTETYPE)
ZCL_NO_DATA_ATTRIBUTE_TYPE = 0
ZCL_BOOLEAN_ATTRIBUTE_TYPE = 16
ZCL_BITMAP8_ATTRIBUTE_TYPE = 24
ZCL_BITMAP16_ATTRIBUTE_TYPE = 25
ZCL_BITMAP32_ATTRIBUTE_TYPE = 27
ZCL_BITMAP64_ATTRIBUTE_TYPE = 31
ZCL_INT8U_ATTRIBUTE_TYPE = 32
ZCL_INT16U_ATTRIBUTE_TYPE = 33
ZCL_INT24U_ATTRIBUTE_TYPE = 34
ZCL_INT32U_ATTRIBUTE_TYPE = 35
ZCL_INT40U_ATTRIBUTE_TYPE = 36
ZCL_INT48U_ATTRIBUTE_TYPE = 37
ZCL_INT56U_ATTRIBUTE_TYPE = 38
ZCL_INT64U_ATTRIBUTE_TYPE = 39
ZCL_INT8S_ATTRIBUTE_TYPE = 40
ZCL_INT16S_ATTRIBUTE_TYPE = 41
ZCL_INT24S_ATTRIBUTE_TYPE = 42
ZCL_INT32S_ATTRIBUTE_TYPE = 43
ZCL_INT40S_ATTRIBUTE_TYPE = 44
ZCL_INT48S_ATTRIBUTE_TYPE = 45
ZCL_INT56S_ATTRIBUTE_TYPE = 46
ZCL_INT64S_ATTRIBUTE_TYPE = 47
ZCL_ENUM8_ATTRIBUTE_TYPE = 48
ZCL_ENUM16_ATTRIBUTE_TYPE = 49
ZCL_SINGLE_ATTRIBUTE_TYPE = 57
ZCL_DOUBLE_ATTRIBUTE_TYPE = 58
ZCL_OCTET_STRING_ATTRIBUTE_TYPE = 65
ZCL_CHAR_STRING_ATTRIBUTE_TYPE = 66
ZCL_LONG_OCTET_STRING_ATTRIBUTE_TYPE = 67
ZCL_LONG_CHAR_STRING_ATTRIBUTE_TYPE = 68
ZCL_ARRAY_ATTRIBUTE_TYPE = 72
ZCL_STRUCT_ATTRIBUTE_TYPE = 76
ZCL_TOD_ATTRIBUTE_TYPE = 224
ZCL_DATE_ATTRIBUTE_TYPE = 225
ZCL_UTC_ATTRIBUTE_TYPE = 226
ZCL_EPOCH_US_ATTRIBUTE_TYPE = 227
ZCL_EPOCH_S_ATTRIBUTE_TYPE = 228
ZCL_SYSTIME_US_ATTRIBUTE_TYPE = 229
ZCL_PERCENT_ATTRIBUTE_TYPE = 230
ZCL_PERCENT100THS_ATTRIBUTE_TYPE = 231
ZCL_CLUSTER_ID_ATTRIBUTE_TYPE = 232
ZCL_ATTRIB_ID_ATTRIBUTE_TYPE = 233
ZCL_FIELD_ID_ATTRIBUTE_TYPE = 234
ZCL_EVENT_ID_ATTRIBUTE_TYPE = 235
ZCL_COMMAND_ID_ATTRIBUTE_TYPE = 236
ZCL_ACTION_ID_ATTRIBUTE_TYPE = 237
ZCL_TRANS_ID_ATTRIBUTE_TYPE = 239
ZCL_NODE_ID_ATTRIBUTE_TYPE = 240
ZCL_VENDOR_ID_ATTRIBUTE_TYPE = 241
ZCL_DEVTYPE_ID_ATTRIBUTE_TYPE = 242
ZCL_FABRIC_ID_ATTRIBUTE_TYPE = 243
ZCL_GROUP_ID_ATTRIBUTE_TYPE = 244
ZCL_STATUS_ATTRIBUTE_TYPE = 245
ZCL_DATA_VER_ATTRIBUTE_TYPE = 246
ZCL_EVENT_NO_ATTRIBUTE_TYPE = 247
ZCL_ENDPOINT_NO_ATTRIBUTE_TYPE = 248
ZCL_FABRIC_IDX_ATTRIBUTE_TYPE = 249
ZCL_IPADR_ATTRIBUTE_TYPE = 250
ZCL_IPV4ADR_ATTRIBUTE_TYPE = 251
ZCL_IPV6ADR_ATTRIBUTE_TYPE = 252
ZCL_IPV6PRE_ATTRIBUTE_TYPE = 253
ZCL_HWADR_ATTRIBUTE_TYPE = 254
ZCL_UNKNOWN_ATTRIBUTE_TYPE = 255



_ATTRIBUTEMETADATA = _descriptor.Descriptor(
  name='AttributeMetadata',
  full_name='chip.rpc.AttributeMetadata',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='endpoint', full_name='chip.rpc.AttributeMetadata.endpoint', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='cluster', full_name='chip.rpc.AttributeMetadata.cluster', index=1,
      number=2, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='attribute_id', full_name='chip.rpc.AttributeMetadata.attribute_id', index=2,
      number=3, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='type', full_name='chip.rpc.AttributeMetadata.type', index=3,
      number=4, type=14, cpp_type=8, label=1,
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
  serialized_start=52,
  serialized_end=167,
)


_ATTRIBUTEDATA = _descriptor.Descriptor(
  name='AttributeData',
  full_name='chip.rpc.AttributeData',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='data_bool', full_name='chip.rpc.AttributeData.data_bool', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='data_uint8', full_name='chip.rpc.AttributeData.data_uint8', index=1,
      number=2, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='data_uint16', full_name='chip.rpc.AttributeData.data_uint16', index=2,
      number=3, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='data_uint32', full_name='chip.rpc.AttributeData.data_uint32', index=3,
      number=4, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='data_bytes', full_name='chip.rpc.AttributeData.data_bytes', index=4,
      number=5, type=12, cpp_type=9, label=1,
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
    _descriptor.OneofDescriptor(
      name='data', full_name='chip.rpc.AttributeData.data',
      index=0, containing_type=None,
      create_key=_descriptor._internal_create_key,
    fields=[]),
  ],
  serialized_start=170,
  serialized_end=304,
)


_ATTRIBUTEWRITE = _descriptor.Descriptor(
  name='AttributeWrite',
  full_name='chip.rpc.AttributeWrite',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='metadata', full_name='chip.rpc.AttributeWrite.metadata', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='data', full_name='chip.rpc.AttributeWrite.data', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
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
  serialized_start=306,
  serialized_end=408,
)

_ATTRIBUTEMETADATA.fields_by_name['type'].enum_type = _ATTRIBUTETYPE
_ATTRIBUTEDATA.oneofs_by_name['data'].fields.append(
  _ATTRIBUTEDATA.fields_by_name['data_bool'])
_ATTRIBUTEDATA.fields_by_name['data_bool'].containing_oneof = _ATTRIBUTEDATA.oneofs_by_name['data']
_ATTRIBUTEDATA.oneofs_by_name['data'].fields.append(
  _ATTRIBUTEDATA.fields_by_name['data_uint8'])
_ATTRIBUTEDATA.fields_by_name['data_uint8'].containing_oneof = _ATTRIBUTEDATA.oneofs_by_name['data']
_ATTRIBUTEDATA.oneofs_by_name['data'].fields.append(
  _ATTRIBUTEDATA.fields_by_name['data_uint16'])
_ATTRIBUTEDATA.fields_by_name['data_uint16'].containing_oneof = _ATTRIBUTEDATA.oneofs_by_name['data']
_ATTRIBUTEDATA.oneofs_by_name['data'].fields.append(
  _ATTRIBUTEDATA.fields_by_name['data_uint32'])
_ATTRIBUTEDATA.fields_by_name['data_uint32'].containing_oneof = _ATTRIBUTEDATA.oneofs_by_name['data']
_ATTRIBUTEDATA.oneofs_by_name['data'].fields.append(
  _ATTRIBUTEDATA.fields_by_name['data_bytes'])
_ATTRIBUTEDATA.fields_by_name['data_bytes'].containing_oneof = _ATTRIBUTEDATA.oneofs_by_name['data']
_ATTRIBUTEWRITE.fields_by_name['metadata'].message_type = _ATTRIBUTEMETADATA
_ATTRIBUTEWRITE.fields_by_name['data'].message_type = _ATTRIBUTEDATA
DESCRIPTOR.message_types_by_name['AttributeMetadata'] = _ATTRIBUTEMETADATA
DESCRIPTOR.message_types_by_name['AttributeData'] = _ATTRIBUTEDATA
DESCRIPTOR.message_types_by_name['AttributeWrite'] = _ATTRIBUTEWRITE
DESCRIPTOR.enum_types_by_name['AttributeType'] = _ATTRIBUTETYPE
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

AttributeMetadata = _reflection.GeneratedProtocolMessageType('AttributeMetadata', (_message.Message,), {
  'DESCRIPTOR' : _ATTRIBUTEMETADATA,
  '__module__' : 'attributes_service_pb2'
  # @@protoc_insertion_point(class_scope:chip.rpc.AttributeMetadata)
  })
_sym_db.RegisterMessage(AttributeMetadata)

AttributeData = _reflection.GeneratedProtocolMessageType('AttributeData', (_message.Message,), {
  'DESCRIPTOR' : _ATTRIBUTEDATA,
  '__module__' : 'attributes_service_pb2'
  # @@protoc_insertion_point(class_scope:chip.rpc.AttributeData)
  })
_sym_db.RegisterMessage(AttributeData)

AttributeWrite = _reflection.GeneratedProtocolMessageType('AttributeWrite', (_message.Message,), {
  'DESCRIPTOR' : _ATTRIBUTEWRITE,
  '__module__' : 'attributes_service_pb2'
  # @@protoc_insertion_point(class_scope:chip.rpc.AttributeWrite)
  })
_sym_db.RegisterMessage(AttributeWrite)



_ATTRIBUTES = _descriptor.ServiceDescriptor(
  name='Attributes',
  full_name='chip.rpc.Attributes',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_start=2505,
  serialized_end=2638,
  methods=[
  _descriptor.MethodDescriptor(
    name='Write',
    full_name='chip.rpc.Attributes.Write',
    index=0,
    containing_service=None,
    input_type=_ATTRIBUTEWRITE,
    output_type=common__pb2._EMPTY,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
  _descriptor.MethodDescriptor(
    name='Read',
    full_name='chip.rpc.Attributes.Read',
    index=1,
    containing_service=None,
    input_type=_ATTRIBUTEMETADATA,
    output_type=_ATTRIBUTEDATA,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
])
_sym_db.RegisterServiceDescriptor(_ATTRIBUTES)

DESCRIPTOR.services_by_name['Attributes'] = _ATTRIBUTES

# @@protoc_insertion_point(module_scope)
