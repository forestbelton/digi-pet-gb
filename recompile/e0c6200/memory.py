import dataclasses
import struct


@dataclasses.dataclass(frozen=True)
class Address:
    bank: int
    page: int
    step: int

    def __lt__(self, other: Address) -> bool:
        return self.raw() < other.raw()

    @staticmethod
    def parse(raw: int) -> Address:
        return Address(
            bank=(raw >> 12) & 1,
            page=(raw >> 8) & 0xF,
            step=raw & 0xFF,
        )

    def raw(self) -> int:
        return (self.bank) << 12 | (self.page << 8) | self.step

    def next(self) -> Address:
        page = self.page
        step = self.step + 1
        if step > 0xFF:
            step = 0
            page += 1
            if page > 0xF:
                page = 0
        return Address(bank=self.bank, page=page, step=step)

    def with_page(self, page: int) -> Address:
        return Address(bank=self.bank, page=page, step=self.step)

    def fmt(self) -> str:
        return f"{self.bank}:{self.page:x}:{self.step:02x}"


@dataclasses.dataclass(frozen=True)
class ROM:
    data: bytes

    def at(self, addr: Address) -> int:
        raw_addr = addr.raw()
        (value,) = struct.unpack(">H", self.data[raw_addr * 2 : raw_addr * 2 + 2])
        return value
