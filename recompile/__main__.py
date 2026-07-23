import hashlib

from recompile.e0c6200 import cfg, indirect, memory
from recompile.ir import lift


def main() -> None:
    with open("DigimonV1JA.bin", "rb") as f:
        data = f.read()
    shasum = hashlib.sha1(data).hexdigest()
    if shasum not in indirect.ROM_INDIRECT_TARGETS:
        raise ValueError(f"unsupported ROM (sha1={shasum})")
    targets = indirect.ROM_INDIRECT_TARGETS[shasum]
    rom = memory.ROM(data=data)

    cfg_blocks = cfg.read_blocks(rom, targets)
    print(f"{len(cfg_blocks.blocks)} blocks identified")

    ir_blocks = lift.blocks(rom, cfg_blocks)
    print(f"{len(ir_blocks)} blocks lifted into IR")


if __name__ == "__main__":
    main()
