from recompile.e0c6200 import cfg, memory


def main() -> None:
    with open("DigimonV1JA.bin", "rb") as f:
        data = f.read()
    blocks = cfg.read_blocks(memory.ROM(data=data))
    num_indirect_blocks = sum(1 for block in blocks.values() if block.indirect)
    print(f"{len(blocks)} blocks identified ({num_indirect_blocks} indirect)")


if __name__ == "__main__":
    main()
