import hashlib

from recompile.e0c6200 import cfg, indirect, memory


def main() -> None:
    with open("DigimonV1JA.bin", "rb") as f:
        data = f.read()
    shasum = hashlib.sha1(data).hexdigest()
    if shasum not in indirect.ROM_INDIRECT_TARGETS:
        raise ValueError(f"unsupported ROM (sha1={shasum})")
    targets = indirect.ROM_INDIRECT_TARGETS[shasum]
    blocks = cfg.read_blocks(memory.ROM(data=data), targets)
    print(f"{len(blocks)} blocks identified")


if __name__ == "__main__":
    main()
