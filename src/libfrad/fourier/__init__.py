from . import profile0, profile1, profile2, profile4, profiles

AVAILABLE = [0, 1, 4]

SEGMAX = [
    0xFFFFFFFF, # Profile 0
    profiles.compact.MAX_SMPL, # Profile 1
    profiles.compact.MAX_SMPL, # Profile 2
    0, # Profile 3
    0xFFFFFFFF, # Profile 4
    0, # Profile 5
    0, # Profile 6
    0, # Profile 7
]

BIT_DEPTHS = [
    profile0.DEPTHS,
    profile1.DEPTHS,
    profile2.DEPTHS,
    [],
    profile4.DEPTHS,
    [],
    [],
    [],
]
