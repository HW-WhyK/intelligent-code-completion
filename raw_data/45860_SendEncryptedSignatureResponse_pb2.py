# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: POGOProtos/Networking/Platform/Responses/SendEncryptedSignatureResponse.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='POGOProtos/Networking/Platform/Responses/SendEncryptedSignatureResponse.proto',
  package='POGOProtos.Networking.Platform.Responses',
  syntax='proto3',
  serialized_pb=_b('\nMPOGOProtos/Networking/Platform/Responses/SendEncryptedSignatureResponse.proto\x12(POGOProtos.Networking.Platform.Responses\"2\n\x1eSendEncryptedSignatureResponse\x12\x10\n\x08received\x18\x01 \x01(\x08\x62\x06proto3')
)
_sym_db.RegisterFileDescriptor(DESCRIPTOR)




_SENDENCRYPTEDSIGNATURERESPONSE = _descriptor.Descriptor(
  name='SendEncryptedSignatureResponse',
  full_name='POGOProtos.Networking.Platform.Responses.SendEncryptedSignatureResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='received', full_name='POGOProtos.Networking.Platform.Responses.SendEncryptedSignatureResponse.received', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=123,
  serialized_end=173,
)

DESCRIPTOR.message_types_by_name['SendEncryptedSignatureResponse'] = _SENDENCRYPTEDSIGNATURERESPONSE

SendEncryptedSignatureResponse = _reflection.GeneratedProtocolMessageType('SendEncryptedSignatureResponse', (_message.Message,), dict(
  DESCRIPTOR = _SENDENCRYPTEDSIGNATURERESPONSE,
  __module__ = 'POGOProtos.Networking.Platform.Responses.SendEncryptedSignatureResponse_pb2'
  # @@protoc_insertion_point(class_scope:POGOProtos.Networking.Platform.Responses.SendEncryptedSignatureResponse)
  ))
_sym_db.RegisterMessage(SendEncryptedSignatureResponse)


# @@protoc_insertion_point(module_scope)
