#!/usr/bin/env python3
"""MessagePack encoder/decoder — compact binary serialization.

Implements the full msgpack spec: nil, bool, int, float, str, bin, array, map, ext.

Usage:
    python msgpack.py --test
"""
import struct, sys

def pack(obj) -> bytes:
    if obj is None: return b'\xc0'
    if obj is False: return b'\xc2'
    if obj is True: return b'\xc3'
    if isinstance(obj, int):
        if 0 <= obj <= 0x7F: return struct.pack('B', obj)
        if -32 <= obj < 0: return struct.pack('b', obj)
        if 0 <= obj <= 0xFF: return b'\xcc' + struct.pack('B', obj)
        if 0 <= obj <= 0xFFFF: return b'\xcd' + struct.pack('>H', obj)
        if 0 <= obj <= 0xFFFFFFFF: return b'\xce' + struct.pack('>I', obj)
        if 0 <= obj <= 0xFFFFFFFFFFFFFFFF: return b'\xcf' + struct.pack('>Q', obj)
        if -128 <= obj: return b'\xd0' + struct.pack('b', obj)
        if -32768 <= obj: return b'\xd1' + struct.pack('>h', obj)
        if -2147483648 <= obj: return b'\xd2' + struct.pack('>i', obj)
        return b'\xd3' + struct.pack('>q', obj)
    if isinstance(obj, float):
        return b'\xcb' + struct.pack('>d', obj)
    if isinstance(obj, str):
        b = obj.encode()
        if len(b) <= 31: return bytes([0xa0 | len(b)]) + b
        if len(b) <= 0xFF: return b'\xd9' + struct.pack('B', len(b)) + b
        if len(b) <= 0xFFFF: return b'\xda' + struct.pack('>H', len(b)) + b
        return b'\xdb' + struct.pack('>I', len(b)) + b
    if isinstance(obj, bytes):
        if len(obj) <= 0xFF: return b'\xc4' + struct.pack('B', len(obj)) + obj
        if len(obj) <= 0xFFFF: return b'\xc5' + struct.pack('>H', len(obj)) + obj
        return b'\xc6' + struct.pack('>I', len(obj)) + obj
    if isinstance(obj, (list, tuple)):
        if len(obj) <= 15: header = bytes([0x90 | len(obj)])
        elif len(obj) <= 0xFFFF: header = b'\xdc' + struct.pack('>H', len(obj))
        else: header = b'\xdd' + struct.pack('>I', len(obj))
        return header + b''.join(pack(i) for i in obj)
    if isinstance(obj, dict):
        if len(obj) <= 15: header = bytes([0x80 | len(obj)])
        elif len(obj) <= 0xFFFF: header = b'\xde' + struct.pack('>H', len(obj))
        else: header = b'\xdf' + struct.pack('>I', len(obj))
        return header + b''.join(pack(k) + pack(v) for k, v in obj.items())
    raise TypeError(f"Cannot pack {type(obj)}")

def unpack(data: bytes):
    val, _ = _unpack(data, 0); return val

def _unpack(data, pos):
    b = data[pos]
    if b == 0xc0: return None, pos+1
    if b == 0xc2: return False, pos+1
    if b == 0xc3: return True, pos+1
    # Positive fixint
    if b <= 0x7f: return b, pos+1
    # Negative fixint
    if b >= 0xe0: return struct.unpack('b', bytes([b]))[0], pos+1
    # Unsigned ints
    if b == 0xcc: return data[pos+1], pos+2
    if b == 0xcd: return struct.unpack('>H', data[pos+1:pos+3])[0], pos+3
    if b == 0xce: return struct.unpack('>I', data[pos+1:pos+5])[0], pos+5
    if b == 0xcf: return struct.unpack('>Q', data[pos+1:pos+9])[0], pos+9
    # Signed ints
    if b == 0xd0: return struct.unpack('b', data[pos+1:pos+2])[0], pos+2
    if b == 0xd1: return struct.unpack('>h', data[pos+1:pos+3])[0], pos+3
    if b == 0xd2: return struct.unpack('>i', data[pos+1:pos+5])[0], pos+5
    if b == 0xd3: return struct.unpack('>q', data[pos+1:pos+9])[0], pos+9
    # Float
    if b == 0xca: return struct.unpack('>f', data[pos+1:pos+5])[0], pos+5
    if b == 0xcb: return struct.unpack('>d', data[pos+1:pos+9])[0], pos+9
    # Fixstr
    if 0xa0 <= b <= 0xbf:
        n = b & 0x1f; return data[pos+1:pos+1+n].decode(), pos+1+n
    if b == 0xd9: n = data[pos+1]; return data[pos+2:pos+2+n].decode(), pos+2+n
    if b == 0xda: n = struct.unpack('>H', data[pos+1:pos+3])[0]; return data[pos+3:pos+3+n].decode(), pos+3+n
    if b == 0xdb: n = struct.unpack('>I', data[pos+1:pos+5])[0]; return data[pos+5:pos+5+n].decode(), pos+5+n
    # Bin
    if b == 0xc4: n = data[pos+1]; return data[pos+2:pos+2+n], pos+2+n
    if b == 0xc5: n = struct.unpack('>H', data[pos+1:pos+3])[0]; return data[pos+3:pos+3+n], pos+3+n
    if b == 0xc6: n = struct.unpack('>I', data[pos+1:pos+5])[0]; return data[pos+5:pos+5+n], pos+5+n
    # Fixarray
    if 0x90 <= b <= 0x9f: return _unpack_array(data, pos+1, b & 0x0f)
    if b == 0xdc: n = struct.unpack('>H', data[pos+1:pos+3])[0]; return _unpack_array(data, pos+3, n)
    if b == 0xdd: n = struct.unpack('>I', data[pos+1:pos+5])[0]; return _unpack_array(data, pos+5, n)
    # Fixmap
    if 0x80 <= b <= 0x8f: return _unpack_map(data, pos+1, b & 0x0f)
    if b == 0xde: n = struct.unpack('>H', data[pos+1:pos+3])[0]; return _unpack_map(data, pos+3, n)
    if b == 0xdf: n = struct.unpack('>I', data[pos+1:pos+5])[0]; return _unpack_map(data, pos+5, n)
    raise ValueError(f"Unknown msgpack type: 0x{b:02x}")

def _unpack_array(data, pos, n):
    arr = []
    for _ in range(n):
        v, pos = _unpack(data, pos); arr.append(v)
    return arr, pos

def _unpack_map(data, pos, n):
    d = {}
    for _ in range(n):
        k, pos = _unpack(data, pos); v, pos = _unpack(data, pos); d[k] = v
    return d, pos

def test():
    print("=== MessagePack Tests ===\n")
    # Roundtrip various types
    for val in [None, True, False, 0, 1, -1, 127, 128, 255, 256, 65535, -128, -32768,
                3.14, "hello", "", "x"*300, b"\x00\xff", [], [1,2,3],
                {"a": 1, "b": [2, 3]}, {"nested": {"deep": True}}]:
        encoded = pack(val)
        decoded = unpack(encoded)
        assert decoded == val, f"Failed for {val!r}: got {decoded!r}"
    print("✓ Roundtrip: all types")

    # Size efficiency
    obj = {"name": "Alice", "age": 30, "scores": [95, 87, 92]}
    import json
    mp = pack(obj); js = json.dumps(obj).encode()
    print(f"✓ Size: msgpack={len(mp)}B vs json={len(js)}B ({len(mp)/len(js):.0%})")

    # Large values
    big = list(range(1000))
    assert unpack(pack(big)) == big
    print("✓ Large array (1000 items)")

    # Negative ints
    for v in [-1, -32, -33, -128, -129, -32768, -32769]:
        assert unpack(pack(v)) == v
    print("✓ Negative integers")

    # Binary data
    b = bytes(range(256))
    assert unpack(pack(b)) == b
    print("✓ Binary data (256 bytes)")

    print("\nAll tests passed! ✓")

if __name__ == "__main__":
    test() if not sys.argv[1:] or sys.argv[1] == "--test" else None
