import argparse
import dataclasses
import pathlib
import re
from typing import Any, Callable

from pyboy import PyBoy

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


Trace = list[tuple[GBAddress, State]]


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


def trace_e0c(e0c_rom_path: str, addr_map: AddressMap, steps: int) -> Trace:
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
    cpu.reset()

    trace: Trace = []
    for _ in range(steps):
        gb_addr = addr_map.e0c_gb_addrs.get(e0c_addr(cpu._PC))
        if gb_addr and (not trace or trace[-1][0] != gb_addr):
            st = cpu.examine()
            ram = list(st["RAM0"]) + list(st["RAM1"]) + list(st["RAM2"])
            trace.append(
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
        cpu.clock()
    return trace


def trace_gb(
    gb_rom_path: str, addr_map: AddressMap, frames: int, max_blocks: int
) -> tuple[Trace, int]:
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

    trace: Trace = []

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
            if not trace or trace[-1][0] != gb_addr:
                trace.append((gb_addr, cap()))

        return cb

    # NB: PyBoy does not expose a single-step method. Instead, we install a hook
    # for each E0C6200 instruction label in the symbol table.
    for gb_addr in addr_map.gb_addr_labels.keys():
        pb.hook_register(gb_addr.bank, gb_addr.addr, mk(gb_addr), None)

    for _ in range(frames):
        pb.tick()
        if len(trace) >= max_blocks:
            break

    final_pc: int = pb.register_file.PC
    pb.stop(save=False)
    return trace, final_pc


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
    args = parser.parse_args()

    addr_map = load_address_map(args.gb_sym)

    e0c_trace = trace_e0c(args.eoc_rom, addr_map, args.steps)
    gb_trace, final_pc = trace_gb(args.gb_rom, addr_map, args.frames, args.max_blocks)
    print(
        f"E0C blocks={len(e0c_trace)}, GB blocks={len(gb_trace)}, GB final PC=${final_pc:04X}"
    )

    for i, (e0c_entry, gb_entry) in enumerate(zip(e0c_trace, gb_trace)):
        e0c_gb_addr, e0c_state = e0c_entry
        gb_addr, gb_state = gb_entry

        e0c_gb_label = addr_map.gb_addr_labels.get(e0c_gb_addr)
        prev_e0c_gb_label = (
            addr_map.gb_addr_labels.get(e0c_trace[i - 1][0]) if i > 0 else "-"
        )

        if e0c_gb_addr != gb_addr:
            gb_label = addr_map.gb_addr_labels.get(gb_addr)
            print(
                f"CONTROL divergence at block {i}: "
                f"E0C={e0c_gb_label} GB={gb_label} (prev {prev_e0c_gb_label})"
            )
            return

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
            return
    num_blocks = min(len(e0c_trace), len(gb_trace))
    print(f"MATCH (control + non-stack state) for {num_blocks=}")


if __name__ == "__main__":
    main()
