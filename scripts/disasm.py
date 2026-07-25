import argparse

from recompile.e0c6200 import disasm, insn, memory


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rom")
    args = parser.parse_args()
    start = memory.Address(bank=0, page=0, step=0)
    addr = start
    with open(args.rom, "rb") as f:
        rom = memory.ROM(f.read())
    assert len(rom.data) % 2 == 0
    for offset in range(len(rom.data) // 2):
        addr = memory.Address.parse(offset)
        insn_str = disasm.render_insn(insn.parse(rom.at(addr)))
        print(f"{addr.fmt()}\t{insn_str}")


if __name__ == "__main__":
    main()
