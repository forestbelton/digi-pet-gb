import dataclasses
from typing import Optional

from recompile.e0c6200 import indirect, insn, memory

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
    calls: list[memory.Address] = dataclasses.field(
        default_factory=list[memory.Address]
    )
    successors: list[memory.Address] = dataclasses.field(
        default_factory=list[memory.Address]
    )


@dataclasses.dataclass
class Program:
    rom: memory.ROM
    blocks: dict[memory.Address, Block]
    targets: indirect.IndirectTargets
    leaders: set[memory.Address]


def _call_successors(rom: memory.ROM, addr: memory.Address) -> list[memory.Address]:
    # A call returns to addr.next(). If the callee performs a RETS, the
    # instruction returned to is actually skipped. As a heuristic, we inspect
    # the instruction following the call to see if it's a PSET: since a PSET
    # can't be skipped over without meaningfully changing the following
    # instruction, we assume there is no possible RETS for this CALL and don't
    # add an additional successor for the skip.
    if isinstance(insn.parse(rom.at(addr.next())), insn.PSET):
        return [addr.next()]
    return [addr.next(), addr.next().next()]


def read_block(
    rom: memory.ROM,
    targets: indirect.IndirectTargets,
    start: memory.Address,
    leaders: set[memory.Address] = set(),
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
                block.successors = _call_successors(rom, addr)
                break
            case insn.CALZ(step):
                block.calls.append(resolve(step).with_page(0))
                block.successors = _call_successors(rom, addr)
                break
            case insn.PSET(p):
                pending = p
            case insn.JP(step):
                block.successors = [resolve(step)]
                break
            case insn.JPBA():
                if addr not in targets:
                    raise ValueError(f"{addr.fmt()}: missing JPBA resolution strategy")
                table = targets[addr]
                for i in range(table.count):
                    entry = memory.Address.parse(table.addr.raw() + i * table.stride)
                    block.successors.append(entry)
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
    targets: indirect.IndirectTargets,
    starts: list[memory.Address] = ENTRYPOINTS,
    leaders: set[memory.Address] = set(),
) -> dict[memory.Address, Block]:
    blocks: dict[memory.Address, Block] = {}
    work = list(starts)
    while len(work) > 0:
        start = work.pop()
        if start in blocks:
            continue
        block = read_block(rom, targets, start, leaders)
        blocks[start] = block
        work.extend(block.successors)
        work.extend(block.calls)
    return blocks


def program(
    rom: memory.ROM,
    targets: indirect.IndirectTargets,
    starts: list[memory.Address] = ENTRYPOINTS,
) -> Program:
    blocks = read_blocks_with_leaders(rom, targets, starts)
    leaders = set(blocks.keys())
    blocks = read_blocks_with_leaders(rom, targets, starts, leaders)
    return Program(
        rom=rom,
        blocks=blocks,
        targets=targets,
        leaders=leaders,
    )
