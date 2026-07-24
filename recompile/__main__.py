import argparse
import hashlib

from recompile.e0c6200 import cfg, indirect, memory
from recompile.codegen import naive
from recompile.ir import lift

ROMFILE = "DigimonV1JA.bin"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", "-o", default="<STDOUT>")
    parser.add_argument("rom", default=ROMFILE)
    args = parser.parse_args()
    with open(args.rom, "rb") as f:
        data = f.read()
    shasum = hashlib.sha1(data).hexdigest()
    if shasum not in indirect.ROM_INDIRECT_TARGETS:
        raise ValueError(f"unsupported ROM (sha1={shasum})")
    cfg_program = cfg.program(
        rom=memory.ROM(data=data),
        targets=indirect.ROM_INDIRECT_TARGETS[shasum],
    )
    ir_program = lift.program(cfg_program)
    asm_source = naive.generate(ir_program)
    if args.output == "<STDOUT>":
        print("\n".join(asm_source))
    else:
        with open(args.output, "w") as outf:
            print("\n".join(asm_source), file=outf)


if __name__ == "__main__":
    main()
