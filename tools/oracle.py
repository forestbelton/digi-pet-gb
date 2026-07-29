import argparse
import dataclasses
import enum
import pathlib
import re
from typing import Any, Callable, Literal

from pyboy import PyBoy

from recompile.e0c6200 import insn, memory
from tools.brickemu.interconnect import Interconnect
from tools.brickemu.cores.E0C6200 import E0C6200

# NB: List of RAM indices to use for comparison. E0C6200 RAM is 0x000-0x27F, but
# since 0xC0-0xFF is the stack region and the recompiler uses the native SM83
# stack instead, we exclude it from consideration.
DATA = [a for a in range(0, 0x280) if not (0xC0 <= a <= 0xFF)]

LABEL_RE = re.compile(r"^rom_(\d+)_([0-9A-F]+)_([0-9A-F]{2})$")

REGISTER_FIELDS = ["A", "B", "IX", "IY", "C", "Z", "D", "I"]

PROGRAM_DESCRIPTION = """
A lock-step differential oracle for comparing GB and E0C6200 behavior.

This oracle operates by:
- Stepping through the vendored BrickEmuPy E0C6200 core one instruction at a time
  to build the reference trace
- Runs the recompiled ROM using PyBoy with a hook on every E0C6200 instruction label
- Compares control flow and architectural state each block boundary

The first divergence between the two execution paths, if it exists, is reported.

With --histogram, the reference trace also yields a dynamic opcode profile: how
often each instruction class actually retires, as opposed to how often it appears
in the ROM. The static and dynamic mixes differ sharply for bulk-init opcodes, so
the profile is what decides whether a codegen optimization buys runtime or only
size.
""".strip()


@dataclasses.dataclass(frozen=True)
class E0CAddress:
    bank: int
    page: int
    step: int


@dataclasses.dataclass(frozen=True)
class GBAddress:
    bank: int
    addr: int


@dataclasses.dataclass
class AddressMap:
    e0c_gb_addrs: dict[E0CAddress, GBAddress]
    gb_addr_labels: dict[GBAddress, str]
    symbols: dict[str, GBAddress]


@dataclasses.dataclass
class State:
    A: int
    B: int
    IX: int
    IY: int
    C: int
    Z: int
    D: int
    I: int
    ram: tuple[int, ...]


Step = tuple[GBAddress, State]

# NB: Retired instruction count keyed by instruction class name. Totals over the
# histogram are instructions retired, which is fewer than the clocks stepped
# whenever the core sits in HALT or SLP.
Histogram = dict[str, int]


class IOAccessType(enum.Enum):
    R = "R"
    W = "W"


@dataclasses.dataclass
class IOAccess:
    type: IOAccessType
    addr: memory.Address


@dataclasses.dataclass
class Trace:
    steps: list[Step]
    io_accesses: list[IOAccess]
    histogram: Histogram | None = dataclasses.field(default=None)
    final_pc: int | None = dataclasses.field(default=None)


def load_address_map(symbol_path: str) -> AddressMap:
    e0c_gb_addrs: dict[E0CAddress, GBAddress] = {}
    gb_addr_labels: dict[GBAddress, str] = {}
    symbols: dict[str, GBAddress] = {}

    for line in open(symbol_path):
        p = line.split()
        if len(p) < 2 or ":" not in p[0]:
            continue

        bank, addr = p[0].split(":")
        gb_addr = GBAddress(bank=int(bank, 16), addr=int(addr, 16))
        symbols[p[1]] = gb_addr

        match = LABEL_RE.match(p[1])
        if match:
            e0c_addr = E0CAddress(
                bank=int(match.group(1), 16),
                page=int(match.group(2), 16),
                step=int(match.group(3), 16),
            )
            e0c_gb_addrs[e0c_addr] = gb_addr
            gb_addr_labels.setdefault(gb_addr, p[1])

    return AddressMap(
        e0c_gb_addrs=e0c_gb_addrs,
        gb_addr_labels=gb_addr_labels,
        symbols=symbols,
    )


def e0c_addr(pc: int) -> E0CAddress:
    return E0CAddress(bank=pc >> 12 & 1, page=pc >> 8 & 0xF, step=pc & 0xFF)


def trace_e0c(e0c_rom_path: str, addr_map: AddressMap, num_steps: int) -> Trace:
    steps: list[Step] = []
    histogram: Histogram = {}
    io_accesses: list[IOAccess] = []

    def add_io_access(
        ty: Literal["R", "W"], addr: int, value: int | None = None
    ) -> None:
        io_accesses.append(
            IOAccess(
                type=IOAccessType[ty],
                addr=memory.Address.parse(addr),
            )
        )

    class Stub:
        def audio_handler(self, channel: int, data: Any) -> None:
            pass

        def serial_tx_handler(self, data: Any) -> None:
            pass

    cpu = E0C6200(
        {
            "rom_path": str(pathlib.Path(e0c_rom_path).resolve()),
            "port_pullup": {"K0": 15, "K1": 15},
            "p3_dedicated": 0,
        },
        1060000,
        Interconnect(Stub()),
    )
    cpu.register_io_handler(add_io_access)
    cpu.reset()
    rom = cpu.get_ROM()

    for _ in range(num_steps):
        gb_addr = addr_map.e0c_gb_addrs.get(e0c_addr(cpu._PC))
        if gb_addr and (not steps or steps[-1][0] != gb_addr):
            st = cpu.examine()
            ram = list(st["RAM0"]) + list(st["RAM1"]) + list(st["RAM2"])
            steps.append(
                (
                    gb_addr,
                    State(
                        A=st["A"],
                        B=st["B"],
                        IX=st["IX"],
                        IY=st["IY"],
                        C=st["CF"],
                        Z=st["ZF"],
                        D=st["DF"],
                        I=st["IF"],
                        ram=tuple(ram[a] for a in DATA),
                    ),
                )
            )
        # NB: The core retires at most one instruction per clock, and none at all
        # while halted, so tally against the instruction counter rather than the
        # loop index.
        pc = cpu._PC
        retired = cpu.istr_counter()
        cpu.clock()
        if cpu.istr_counter() != retired:
            name = insn.INSN_PARSERS[rom.get_word(pc * 2)].__name__
            histogram[name] = histogram.get(name, 0) + 1
    return Trace(
        steps=steps,
        io_accesses=io_accesses,
        histogram=histogram,
    )


def trace_gb(
    gb_rom_path: str, addr_map: AddressMap, frames: int, max_blocks: int
) -> Trace:
    pb = PyBoy(gb_rom_path, window="null")
    M = pb.memory
    A = addr_map.symbols["hA"].addr
    B = addr_map.symbols["hB"].addr
    F = addr_map.symbols["hF"].addr
    XP = addr_map.symbols["hXP"].addr
    XHL = addr_map.symbols["hXHL"].addr
    YP = addr_map.symbols["hYP"].addr
    YHL = addr_map.symbols["hYHL"].addr
    W = addr_map.symbols["wRAM"].addr
    _read_ram = addr_map.symbols["_read_ram.read_io"]
    _write_ram = addr_map.symbols["_write_ram.write_io"]

    steps: list[Step] = []
    io_accesses: list[IOAccess] = []

    def cap() -> State:
        hf: int = M[F]
        return State(
            A=M[A],
            B=M[B],
            IX=(M[XP] << 8) | M[XHL],
            IY=(M[YP] << 8) | M[YHL],
            C=hf & 1,
            Z=hf >> 1 & 1,
            D=hf >> 2 & 1,
            I=hf >> 3 & 1,
            ram=tuple(M[W + a] for a in DATA),
        )

    def mk(gb_addr: GBAddress) -> Callable[[Any], None]:
        def cb(_ctx: Any):
            if not steps or steps[-1][0] != gb_addr:
                steps.append((gb_addr, cap()))

        return cb

    # NB: PyBoy does not expose a single-step method. Instead, we install a hook
    # for each E0C6200 instruction label in the symbol table.
    for gb_addr in addr_map.gb_addr_labels.keys():
        pb.hook_register(gb_addr.bank, gb_addr.addr, mk(gb_addr), None)

    def add_io_access(type: IOAccessType) -> Callable[[Any], None]:
        def cb(_ctx: Any):
            idx_ptr = pb.register_file.HL
            step = M[idx_ptr]
            io_accesses.append(
                IOAccess(type=type, addr=memory.Address(bank=0, page=0xF, step=step))
            )

        return cb

    pb.hook_register(
        _read_ram.bank, _read_ram.addr, add_io_access(IOAccessType.R), None
    )
    pb.hook_register(
        _write_ram.bank, _write_ram.addr, add_io_access(IOAccessType.W), None
    )

    for _ in range(frames):
        pb.tick()
        if len(steps) >= max_blocks:
            break

    pb.stop(save=False)
    return Trace(
        steps=steps,
        io_accesses=io_accesses,
        final_pc=pb.register_file.PC,
    )


def print_histogram(histogram: Histogram, clocks: int) -> None:
    retired = sum(histogram.values())
    print(f"Dynamic opcode histogram: {retired} retired over {clocks} clocks")
    for name, count in sorted(histogram.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {name:<16} {count:>8} {100 * count / retired:>5.1f}%")


def main():
    parser = argparse.ArgumentParser(description=PROGRAM_DESCRIPTION)
    parser.add_argument("--steps", type=int, default=12000, help="E0C6200 instructions")
    parser.add_argument("--frames", type=int, default=500, help="GB frame cap")
    parser.add_argument("--max-blocks", type=int, default=5000, help="GB block budget")
    parser.add_argument(
        "--eoc-rom", type=str, default="DigimonV1JA.bin", help="E0C6200 ROM"
    )
    parser.add_argument("--gb-rom", type=str, default="DigimonV1JA.gb", help="GB ROM")
    parser.add_argument(
        "--gb-sym", type=str, default="DigimonV1JA.sym", help="GB symbols"
    )
    parser.add_argument(
        "--histogram", action="store_true", help="print dynamic opcode histogram"
    )
    parser.add_argument("--print-io", action="store_true", help="print I/O accesses")
    args = parser.parse_args()

    addr_map = load_address_map(args.gb_sym)

    e0c_trace = trace_e0c(args.eoc_rom, addr_map, args.steps)
    if args.histogram:
        assert e0c_trace.histogram is not None
        print_histogram(e0c_trace.histogram, args.steps)

    gb_trace = trace_gb(args.gb_rom, addr_map, args.frames, args.max_blocks)
    print(
        f"E0C blocks={len(e0c_trace.steps)}, "
        f"GB blocks={len(gb_trace.steps)}, "
        f"GB final PC=${gb_trace.final_pc:04X}"
    )

    match = True
    for i, (e0c_entry, gb_entry) in enumerate(zip(e0c_trace.steps, gb_trace.steps)):
        e0c_gb_addr, e0c_state = e0c_entry
        gb_addr, gb_state = gb_entry

        e0c_gb_label = addr_map.gb_addr_labels.get(e0c_gb_addr)
        prev_e0c_gb_label = (
            addr_map.gb_addr_labels.get(e0c_trace.steps[i - 1][0]) if i > 0 else "-"
        )

        if e0c_gb_addr != gb_addr:
            gb_label = addr_map.gb_addr_labels.get(gb_addr)
            print(
                f"CONTROL divergence at block {i}: "
                f"E0C={e0c_gb_label} GB={gb_label} (prev {prev_e0c_gb_label})"
            )
            match = False
            break

        mismatches: list[str] = []
        for field in REGISTER_FIELDS:
            e0c_field = getattr(e0c_state, field)
            gb_field = getattr(gb_state, field)
            if e0c_field != gb_field:
                mismatches.append(f"{field}: E0C={e0c_field:X} GB={gb_field:X}")

        for k in range(len(DATA)):
            e0c_byte = e0c_state.ram[k]
            gb_byte = gb_state.ram[k]
            if e0c_byte != gb_byte:
                mismatches.append(
                    f"RAM[{DATA[k]:03X}]: E0C={e0c_byte:X} GB={gb_byte:X}"
                )

        if len(mismatches) > 0:
            print(
                f"STATE divergence at block {i} ({e0c_gb_label}), "
                f"prev={prev_e0c_gb_label}:"
            )
            for mismatch in mismatches:
                print(f"  {mismatch}")
            match = False
            break

    if match:
        num_blocks = min(len(e0c_trace.steps), len(gb_trace.steps))
        print(f"MATCH (control + non-stack state) for {num_blocks=}")

    for i, (e0c_io, gb_io) in enumerate(
        zip(e0c_trace.io_accesses, gb_trace.io_accesses)
    ):
        if e0c_io != gb_io:
            print(
                f"IO divergence at access {i}, "
                f"E0C={e0c_io.addr.fmt()}, "
                f"GB={gb_io.addr.fmt()}"
            )
            break

    if args.print_io:
        for e0c_io in e0c_trace.io_accesses:
            print(f"{e0c_io.type.value} {e0c_io.addr.fmt()}")


if __name__ == "__main__":
    main()
