import dataclasses

from recompile.e0c6200 import memory


@dataclasses.dataclass
class DispatchTable:
    addr: memory.Address
    stride: int = dataclasses.field(default=1)
    count: int = dataclasses.field(default=0x10)


@dataclasses.dataclass
class ReturnTable:
    addr: memory.Address
    length: int


IndirectTarget = DispatchTable | ReturnTable

IndirectTargets = dict[memory.Address, IndirectTarget]

# NB: Statically resolved JPBA targets for each supported ROM. Encoding these
# as configuration saves us from having to do pattern recognition on the ROM to
# determine what the indirect jump targets are, which feels like a suitable
# tradeoff for a fixed set of old ROMs.
ROM_INDIRECT_TARGETS: dict[str, IndirectTargets] = {
    "1dde9b0aa81c8f4a1e22d3a79d4743833fc6cba7": {
        memory.Address(bank=0, page=0, step=0xFB): DispatchTable(
            addr=memory.Address(bank=0, page=0xF, step=0x00),
        ),
        memory.Address(bank=0, page=0x4, step=0x0F): ReturnTable(
            addr=memory.Address(bank=0, page=4, step=0),
            length=9,
        ),
        memory.Address(bank=0, page=0x5, step=0x20): ReturnTable(
            addr=memory.Address(bank=0, page=5, step=0),
            length=16,
        ),
        memory.Address(bank=0, page=0x6, step=0x33): ReturnTable(
            addr=memory.Address(bank=0, page=6, step=0x10),
            length=32,
        ),
        memory.Address(bank=0, page=0x6, step=0x4B): ReturnTable(
            addr=memory.Address(bank=0, page=6, step=0x02),
            length=14,
        ),
        memory.Address(bank=0, page=0xC, step=0x27): DispatchTable(
            addr=memory.Address(bank=0, page=0xC, step=0x00)
        ),
        memory.Address(bank=0, page=0xD, step=0x16): DispatchTable(
            addr=memory.Address(bank=0, page=0xD, step=0x00)
        ),
        memory.Address(bank=0, page=0xE, step=0x14): DispatchTable(
            addr=memory.Address(bank=0, page=0xE, step=0x00)
        ),
        memory.Address(bank=0, page=0xF, step=0x23): DispatchTable(
            addr=memory.Address(bank=0, page=0xF, step=0x10)
        ),
        memory.Address(bank=1, page=0x2, step=0x36): DispatchTable(
            addr=memory.Address(bank=1, page=0x2, step=0x00),
            stride=2,
        ),
        memory.Address(bank=1, page=0x1, step=0x22): DispatchTable(
            addr=memory.Address(bank=1, page=0x1, step=0x10)
        ),
        memory.Address(bank=1, page=0x2, step=0xBB): DispatchTable(
            addr=memory.Address(bank=1, page=0x2, step=0x20)
        ),
        memory.Address(bank=1, page=0x3, step=0x13): DispatchTable(
            addr=memory.Address(bank=1, page=0x3, step=0x00)
        ),
        memory.Address(bank=1, page=0x4, step=0x12): DispatchTable(
            addr=memory.Address(bank=1, page=0x4, step=0x00)
        ),
        memory.Address(bank=1, page=0x5, step=0x12): DispatchTable(
            addr=memory.Address(bank=1, page=0x5, step=0x00)
        ),
        memory.Address(bank=1, page=0x6, step=0x13): DispatchTable(
            addr=memory.Address(bank=1, page=0x6, step=0x00)
        ),
        memory.Address(bank=1, page=0x7, step=0x13): DispatchTable(
            addr=memory.Address(bank=1, page=0x7, step=0x00)
        ),
        memory.Address(bank=1, page=0x8, step=0x13): DispatchTable(
            addr=memory.Address(bank=1, page=0x8, step=0x00)
        ),
        memory.Address(bank=1, page=0x9, step=0x12): DispatchTable(
            addr=memory.Address(bank=1, page=0x9, step=0x00)
        ),
        memory.Address(bank=1, page=0xA, step=0x12): DispatchTable(
            addr=memory.Address(bank=1, page=0xA, step=0x00)
        ),
        memory.Address(bank=1, page=0xB, step=0x13): DispatchTable(
            addr=memory.Address(bank=1, page=0xB, step=0x00)
        ),
        memory.Address(bank=1, page=0xC, step=0x13): DispatchTable(
            addr=memory.Address(bank=1, page=0xC, step=0x00)
        ),
        memory.Address(bank=1, page=0xD, step=0x13): DispatchTable(
            addr=memory.Address(bank=1, page=0xD, step=0x00)
        ),
        memory.Address(bank=1, page=0xF, step=0x12): DispatchTable(
            addr=memory.Address(bank=1, page=0xF, step=0x00)
        ),
    }
}
