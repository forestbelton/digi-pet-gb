import abc
import dataclasses
import enum
from typing import Self, Type


class Insn(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def parse(cls, insn: int) -> Self: ...


@dataclasses.dataclass
class Insn0(Insn, abc.ABC):
    @classmethod
    def parse(cls, insn: int) -> Self:
        return cls()


@dataclasses.dataclass
class InsnE(Insn, abc.ABC):
    e: int

    @classmethod
    def parse(cls, insn: int) -> Self:
        return cls(e=insn & 0xFF)


@dataclasses.dataclass
class InsnI(Insn, abc.ABC):
    i: int

    @classmethod
    def parse(cls, insn: int) -> Self:
        return cls(i=insn & 0xF)


@dataclasses.dataclass
class InsnN(Insn, abc.ABC):
    n: int

    @classmethod
    def parse(cls, insn: int) -> Self:
        return cls(n=insn & 0xF)


@dataclasses.dataclass
class InsnR(Insn, abc.ABC):
    r: int

    @classmethod
    def parse(cls, insn: int) -> Self:
        return cls(r=insn & 0x3)


@dataclasses.dataclass
class InsnRI(Insn, abc.ABC):
    r: int
    i: int

    @classmethod
    def parse(cls, insn: int) -> Self:
        return cls(r=(insn >> 4) & 0x3, i=insn & 0xF)


@dataclasses.dataclass
class InsnRQ(Insn, abc.ABC):
    r: int
    q: int

    @classmethod
    def parse(cls, insn: int) -> Self:
        return cls(r=(insn >> 2) & 0x3, q=insn & 0x3)


@dataclasses.dataclass
class InsnS(Insn, abc.ABC):
    s: int

    @classmethod
    def parse(cls, insn: int) -> Self:
        return cls(s=insn & 0xFF)


class InsnUnknown(Insn):
    @classmethod
    def parse(cls, insn: int) -> Self:
        raise ValueError(f"unknown opcode 0x{insn:03x}")


class ACPX_MX_R(InsnR): ...


class ACPY_MY_R(InsnR): ...


class ADC_R_I(InsnRI): ...


class ADC_R_Q(InsnRQ): ...


class ADC_XH_I(InsnI): ...


class ADC_XL_I(InsnI): ...


class ADC_YH_I(InsnI): ...


class ADC_YL_I(InsnI): ...


class ADD_R_I(InsnRI): ...


class ADD_R_Q(InsnRQ): ...


class AND_R_I(InsnRI): ...


class AND_R_Q(InsnRQ): ...


class CALL(InsnS): ...


class CALZ(InsnS): ...


class CP_R_I(InsnRI): ...


class CP_R_Q(InsnRQ): ...


class CP_XH_I(InsnI): ...


class CP_XL_I(InsnI): ...


class CP_YH_I(InsnI): ...


class CP_YL_I(InsnI): ...


class DEC_MN(InsnN): ...


class DEC_SP(Insn0): ...


class FAN_R_I(InsnRI): ...


class FAN_R_Q(InsnRQ): ...


class HALT(Insn0): ...


class INC_MN(InsnN): ...


class INC_SP(Insn0): ...


class JP(InsnS): ...


class JPBA(Insn0): ...


class FlagCondition(enum.Enum):
    CARRY = "C"
    NOT_CARRY = "NC"
    ZERO = "Z"
    NOT_ZERO = "NZ"


COND_FLAGS: dict[int, dict[int, FlagCondition]] = {
    0: {
        0: FlagCondition.CARRY,
        1: FlagCondition.NOT_CARRY,
    },
    1: {
        0: FlagCondition.ZERO,
        1: FlagCondition.NOT_ZERO,
    },
}


@dataclasses.dataclass
class JP_COND(InsnS):
    c: FlagCondition

    @classmethod
    def parse(cls, insn: int) -> Self:
        c_or_z = (insn >> 10) & 1
        y_or_n = (insn >> 8) & 1
        return cls(s=insn & 0xFF, c=COND_FLAGS[c_or_z][y_or_n])


class LBPX_MX_E(InsnE): ...


class LD_A_MN(InsnN): ...


class LD_B_MN(InsnN): ...


class LD_MN_A(InsnN): ...


class LD_MN_B(InsnN): ...


class LD_R_I(InsnRI): ...


class LD_R_SPH(InsnR): ...


class LD_R_SPL(InsnR): ...


class LD_R_Q(InsnRQ): ...


class LD_R_XP(InsnR): ...


class LD_R_XH(InsnR): ...


class LD_R_XL(InsnR): ...


class LD_R_YP(InsnR): ...


class LD_R_YH(InsnR): ...


class LD_R_YL(InsnR): ...


class LD_SPL_R(InsnR): ...


class LD_SPH_R(InsnR): ...


class LD_X_E(InsnE): ...


class LD_XH_R(InsnR): ...


class LD_XL_R(InsnR): ...


class LD_XP_R(InsnR): ...


class LD_Y_E(InsnE): ...


class LD_YH_R(InsnR): ...


class LD_YL_R(InsnR): ...


class LD_YP_R(InsnR): ...


class LDPX_MX_I(InsnI): ...


class LDPX_R_Q(InsnRQ): ...


class LDPY_MY_I(InsnI): ...


class LDPY_R_Q(InsnRQ): ...


class OR_R_I(InsnRI): ...


class OR_R_Q(InsnRQ): ...


class NOP5(Insn0): ...


class NOP7(Insn0): ...


class POP_F(Insn0): ...


class POP_R(InsnR): ...


class POP_XH(Insn0): ...


class POP_XL(Insn0): ...


class POP_XP(Insn0): ...


class POP_YH(Insn0): ...


class POP_YL(Insn0): ...


class POP_YP(Insn0): ...


@dataclasses.dataclass
class PSET(Insn):
    p: int

    @classmethod
    def parse(cls, insn: int) -> Self:
        return cls(p=insn & 0x1F)


class PUSH_F(Insn0): ...


class PUSH_R(InsnR): ...


class PUSH_XH(Insn0): ...


class PUSH_XL(Insn0): ...


class PUSH_XP(Insn0): ...


class PUSH_YH(Insn0): ...


class PUSH_YL(Insn0): ...


class PUSH_YP(Insn0): ...


class RET(Insn0): ...


class RETD(InsnE): ...


class RETS(Insn0): ...


class RLC(InsnR): ...


class RRC(InsnR): ...


@dataclasses.dataclass
class RST(InsnI): ...


class SBC_R_I(InsnRI): ...


class SBC_R_Q(InsnRQ): ...


class SCPX_MX_R(InsnR): ...


class SCPY_MY_R(InsnR): ...


class SET(InsnI): ...


class SUB_R_Q(InsnRQ): ...


class SLP(Insn0): ...


class XOR_R_I(InsnRI): ...


class XOR_R_Q(InsnRQ): ...


INSN_COUNT = 0x1000

INSN_TABLE: list[tuple[int | tuple[int, int], Type[Insn]]] = [
    ((0x000, 0x0FF), JP),
    ((0x100, 0x1FF), RETD),
    ((0x200, 0x3FF), JP_COND),
    ((0x400, 0x4FF), CALL),
    ((0x500, 0x5FF), CALZ),
    ((0x600, 0x7FF), JP_COND),
    ((0x800, 0x8FF), LD_Y_E),
    ((0x900, 0x9FF), LBPX_MX_E),
    ((0xA00, 0xA0F), ADC_XH_I),
    ((0xA10, 0xA1F), ADC_XL_I),
    ((0xA20, 0xA2F), ADC_YH_I),
    ((0xA30, 0xA3F), ADC_YL_I),
    ((0xA40, 0xA4F), CP_XH_I),
    ((0xA50, 0xA5F), CP_XL_I),
    ((0xA60, 0xA6F), CP_YH_I),
    ((0xA70, 0xA7F), CP_YL_I),
    ((0xA80, 0xA8F), ADD_R_Q),
    ((0xA90, 0xA9F), ADC_R_Q),
    ((0xAA0, 0xAAF), SUB_R_Q),
    ((0xAB0, 0xABF), SBC_R_Q),
    ((0xAC0, 0xACF), AND_R_Q),
    ((0xAD0, 0xADF), OR_R_Q),
    ((0xAE0, 0xAEF), XOR_R_Q),
    ((0xAF0, 0xAFF), RLC),
    ((0xB00, 0xBFF), LD_X_E),
    ((0xC00, 0xC3F), ADD_R_I),
    ((0xC40, 0xC7F), ADC_R_I),
    ((0xC80, 0xCBF), AND_R_I),
    ((0xCC0, 0xCFF), OR_R_I),
    ((0xD00, 0xD3F), XOR_R_I),
    ((0xD40, 0xD7F), SBC_R_I),
    ((0xD80, 0xDBF), FAN_R_I),
    ((0xDC0, 0xDFF), CP_R_I),
    ((0xE00, 0xE3F), LD_R_I),
    ((0xE40, 0xE5F), PSET),
    ((0xE60, 0xE6F), LDPX_MX_I),
    ((0xE70, 0xE7F), LDPY_MY_I),
    ((0xE80, 0xE83), LD_XP_R),
    ((0xE84, 0xE87), LD_XH_R),
    ((0xE88, 0xE8B), LD_XL_R),
    ((0xE8C, 0xE8F), RRC),
    ((0xE90, 0xE93), LD_YP_R),
    ((0xE94, 0xE97), LD_YH_R),
    ((0xE98, 0xE9B), LD_YL_R),
    ((0xEA0, 0xEA3), LD_R_XP),
    ((0xEA4, 0xEA7), LD_R_XH),
    ((0xEA8, 0xEAB), LD_R_XL),
    ((0xEB0, 0xEB3), LD_R_YP),
    ((0xEB4, 0xEB7), LD_R_YH),
    ((0xEB8, 0xEBB), LD_R_YL),
    ((0xEC0, 0xECF), LD_R_Q),
    ((0xEE0, 0xEEF), LDPX_R_Q),
    ((0xEF0, 0xEFF), LDPY_R_Q),
    ((0xF00, 0xF0F), CP_R_Q),
    ((0xF10, 0xF1F), FAN_R_Q),
    ((0xF28, 0xF2B), ACPX_MX_R),
    ((0xF2C, 0xF2F), ACPY_MY_R),
    ((0xF38, 0xF3B), SCPX_MX_R),
    ((0xF3C, 0xF3F), SCPY_MY_R),
    ((0xF40, 0xF4F), SET),
    ((0xF50, 0xF5F), RST),
    ((0xF60, 0xF6F), INC_MN),
    ((0xF70, 0xF7F), DEC_MN),
    ((0xF80, 0xF8F), LD_MN_A),
    ((0xF90, 0xF9F), LD_MN_B),
    ((0xFA0, 0xFAF), LD_A_MN),
    ((0xFB0, 0xFBF), LD_B_MN),
    ((0xFC0, 0xFC3), PUSH_R),
    (0xFC4, PUSH_XP),
    (0xFC5, PUSH_XH),
    (0xFC6, PUSH_XL),
    (0xFC7, PUSH_YP),
    (0xFC8, PUSH_YH),
    (0xFC9, PUSH_YL),
    (0xFCA, PUSH_F),
    (0xFCB, DEC_SP),
    ((0xFD0, 0xFD3), POP_R),
    (0xFD4, POP_XP),
    (0xFD5, POP_XH),
    (0xFD6, POP_XL),
    (0xFD7, POP_YP),
    (0xFD8, POP_YH),
    (0xFD9, POP_YL),
    (0xFDA, POP_F),
    (0xFDB, INC_SP),
    (0xFDE, RETS),
    (0xFDF, RET),
    ((0xFE0, 0xFE3), LD_SPH_R),
    ((0xFE4, 0xFE7), LD_R_SPH),
    (0xFE8, JPBA),
    ((0xFF0, 0xFF3), LD_SPL_R),
    ((0xFF4, 0xFF7), LD_R_SPL),
    (0xFF8, HALT),
    (0xFF9, SLP),
    (0xFFB, NOP5),
    (0xFFF, NOP7),
]

INSN_PARSERS: dict[int, Type[Insn]] = {}

for i in range(INSN_COUNT):
    INSN_PARSERS[i] = InsnUnknown
for bound, parser in INSN_TABLE:
    if isinstance(bound, int):
        if INSN_PARSERS[bound] != InsnUnknown:
            raise ValueError(f"parser overlaps at 0x{bound:03x}")
        INSN_PARSERS[bound] = parser
    else:
        start, end = bound
        for i in range(start, end + 1):
            if INSN_PARSERS[i] != InsnUnknown:
                raise ValueError(f"parser overlaps at 0x{i:03x}")
            INSN_PARSERS[i] = parser


def parse(insn: int) -> Insn:
    return INSN_PARSERS[insn].parse(insn)
