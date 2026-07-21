import dataclasses
from typing import Optional

from recompile.e0c6200 import insn, memory

ENTRYPOINTS: list[memory.Address] = [
    memory.Address.parse(addr)
    for addr in [
        0x100,
        0x102,
        0x104,
        0x106,
        0x108,
        0x10A,
        0x10C,
    ]
]


@dataclasses.dataclass
class Block:
    start: memory.Address
    indirect: bool = dataclasses.field(default=False)
    calls: list[memory.Address] = dataclasses.field(
        default_factory=list[memory.Address]
    )
    successors: list[memory.Address] = dataclasses.field(
        default_factory=list[memory.Address]
    )


def read_block(
    rom: memory.ROM, start: memory.Address, leaders: set[memory.Address] = set()
) -> Block:
    block = Block(start=start)
    addr = start
    pending: Optional[int] = None

    def resolve(step: int) -> memory.Address:
        bank: int
        page: int
        if pending is not None:
            bank = (pending >> 4) & 1
            page = pending & 0xF
        else:
            bank = addr.bank
            page = addr.page
        return memory.Address(bank=bank, page=page, step=step)

    while True:
        raw_insn = rom.at(addr)
        match insn.parse(raw_insn):
            case insn.CALL(step):
                block.calls.append(resolve(step))
                pending = None
            case insn.CALZ(step):
                block.calls.append(resolve(step).with_page(0))
                pending = None
            case insn.PSET(p):
                pending = p
            case insn.JP(step):
                block.successors = [resolve(step)]
                break
            case insn.JPBA():
                block.indirect = True
                break
            case insn.JP_COND(step):
                block.successors = [resolve(step), addr.next()]
                break
            case insn.RET() | insn.RETD() | insn.RETS():
                break
            case _:
                pending = None

        addr = addr.next()
        if addr in leaders:
            block.successors = [addr]
            break

    return block


def read_blocks_with_leaders(
    rom: memory.ROM,
    starts: list[memory.Address] = ENTRYPOINTS,
    leaders: set[memory.Address] = set(),
) -> dict[memory.Address, Block]:
    blocks: dict[memory.Address, Block] = {}
    work = list(starts)
    while len(work) > 0:
        start = work.pop()
        if start in blocks:
            continue
        block = read_block(rom, start, leaders)
        blocks[start] = block
        work.extend(block.successors)
        work.extend(block.calls)
    return blocks


def read_blocks(
    rom: memory.ROM,
    starts: list[memory.Address] = ENTRYPOINTS,
) -> dict[memory.Address, Block]:
    blocks = read_blocks_with_leaders(rom, starts)
    leaders = set(blocks.keys())
    return read_blocks_with_leaders(rom, starts, leaders)
