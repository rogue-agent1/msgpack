#!/usr/bin/env python3
"""MessagePack encoder/decoder (subset)."""
import sys, struct
def pack(obj):
    if obj is None: return b'\xc0'
    if obj is True: return b'\xc3'
    if obj is False: return b'\xc2'
    if isinstance(obj,int):
        if 0<=obj<128: return bytes([obj])
        if -32<=obj<0: return struct.pack('b',obj)
        if 0<=obj<256: return b'\xcc'+struct.pack('B',obj)
        if 0<=obj<65536: return b'\xcd'+struct.pack('>H',obj)
        return b'\xce'+struct.pack('>I',obj)
    if isinstance(obj,str):
        b=obj.encode()
        if len(b)<32: return bytes([0xa0|len(b)])+b
        return b'\xd9'+bytes([len(b)])+b
    if isinstance(obj,list):
        if len(obj)<16: return bytes([0x90|len(obj)])+b''.join(pack(x) for x in obj)
        return b'\xdc'+struct.pack('>H',len(obj))+b''.join(pack(x) for x in obj)
    if isinstance(obj,dict):
        if len(obj)<16: return bytes([0x80|len(obj)])+b''.join(pack(k)+pack(v) for k,v in obj.items())
    return b''
data={"name":"Rogue","age":1,"tools":["python","git"],"active":True}
packed=pack(data)
print(f"Original: {data}\nPacked: {packed.hex()} ({len(packed)} bytes vs {len(str(data))} chars)")
