from typing import TypedDict

from tools.brickemu.cores.rom import ROM
from tools.brickemu.interconnect import Interconnect

class Mask(TypedDict):
    rom_path: str
    port_pullup: dict[str, int]
    p3_dedicated: int

class State(TypedDict):
    A: int
    B: int
    IX: int
    IY: int
    CF: int
    ZF: int
    DF: int
    IF: int
    RAM0: list[int]
    RAM1: list[int]
    RAM2: list[int]

class E0C6200:
    _PC: int

    def __init__(self, mask: Mask, clock: int, interconnect: Interconnect) -> None: ...
    def clock(self) -> None: ...
    def examine(self) -> State: ...
    def get_ROM(self) -> ROM: ...
    def istr_counter(self) -> int: ...
    def reset(self) -> None: ...
