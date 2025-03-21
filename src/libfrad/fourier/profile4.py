import numpy as np

DEPTHS = (12, 16, 24, 32, 48, 64)
DTYPES = {128:'f16',64:'f8',48:'f8',32:'f4',24:'f4',16:'f2',12:'f2'}
FLOAT_DR = (
    np.finfo('f2').max,
    np.finfo('f2').max,
    np.finfo('f4').max,
    np.finfo('f4').max,
    np.finfo('f8').max,
    np.finfo('f8').max
)

def analogue(pcm: np.ndarray, bits: int, srate: int, little_endian: bool) -> tuple[bytes, int, int, int]:
    if bits not in DEPTHS: bits = 16
    be = not little_endian
    endian = be and '>' or '<'
    channels = len(pcm[0])

    # Overflow check & Increasing bit depth
    while np.max(np.abs(pcm)) > FLOAT_DR[DEPTHS.index(bits)]:
        if bits == 128: raise Exception('Overflow with reaching the max bit depth.')
        bits = {12:16, 16:24, 24:32, 32:48, 48:64, 64:128}.get(bits, 128)

    # Ravelling and packing
    if bits%8!=0: endian = '>'
    frad: bytes = pcm.ravel().astype(endian+DTYPES[bits]).tobytes()

    # Cutting off bits
    if bits in (128, 64, 32, 16):
        pass
    elif bits in (48, 24):
        frad = b''.join([be and frad[i:i+(bits//8)] or frad[i+(bits//24):i+(bits//6)] for i in range(0, len(frad), bits//6)])
    elif bits == 12:
        hexa = frad.hex()
        hexa = ''.join([hexa[i:i+3] for i in range(0, len(hexa), 4)])
        if len(hexa)%2!=0: hexa+='0'
        frad = bytes.fromhex(hexa)
    else: raise Exception('Illegal bits value.')

    return frad, DEPTHS.index(bits), channels, srate

def digital(frad: bytes, fb: int, channels: int, little_endian: bool) -> np.ndarray:
    be = not little_endian
    endian = be and '>' or '<'
    bits = DEPTHS[fb]

    # Padding bits
    if bits % 3 != 0: pass
    elif bits in (24, 48):
        frad = b''.join([be and frad[i:i+(bits//8)]+(b'\x00'*(bits//24)) or (b'\x00'*(bits//24))+frad[i:i+(bits//8)] for i in range(0, len(frad), bits//8)])
    elif bits == 12:
        hexa = frad.hex()
        if len(hexa)%3!=0: hexa=hexa[:-1]
        frad = bytes.fromhex(''.join([f'{hexa[i:i+3]}0' for i in range(0, len(hexa), 3)]))
    else: raise Exception('Illegal bits value.')

    # Unpacking and unravelling
    if bits%8!=0: endian = '>'
    pcm: np.ndarray = np.frombuffer(frad, f'{endian}{DTYPES[bits]}').astype(float).reshape(-1, channels)

    # Removing potential Infinities and Non-numbers
    return np.where(np.isnan(pcm) | np.isinf(pcm), 0, pcm)
