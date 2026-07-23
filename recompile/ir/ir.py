import dataclasses
import enum
from typing import Literal, TypeIs

from recompile.e0c6200 import memory


class Flag(enum.Enum):
    I = "I"
    D = "D"
    Z = "Z"
    C = "C"

    @property
    def reads(self) -> set[Location]:
        return {self}

    @property
    def writes(self) -> set[Location]:
        return {self}

    @property
    def mask(self) -> int:
        BIT_INDEXES = {
            Flag.C: 0,
            Flag.Z: 1,
            Flag.D: 2,
            Flag.I: 3,
        }
        return 1 << BIT_INDEXES[self]


class Register(enum.Enum):
    A = "A"
    B = "B"
    F = "F"
    XH = "XH"
    XL = "XL"
    XP = "XP"
    YH = "YH"
    YL = "YL"
    YP = "YP"

    @property
    def reads(self) -> set[Location]:
        if self == Register.F:
            return {Flag.I, Flag.D, Flag.Z, Flag.C}
        return {self}

    @property
    def writes(self) -> set[Location]:
        if self == Register.F:
            return {Flag.I, Flag.D, Flag.Z, Flag.C}
        return {self}


@dataclasses.dataclass(frozen=True)
class Pointer:
    loc: Literal["X", "Y"]

    @property
    def reads(self) -> set[Location]:
        match self.loc:
            case "X":
                return {Register.XP, Register.XH, Register.XL}
            case "Y":
                return {Register.YP, Register.YH, Register.YL}

    @property
    def writes(self) -> set[Location]:
        match self.loc:
            case "X":
                return {Register.XP, Register.XH, Register.XL}
            case "Y":
                return {Register.YP, Register.YH, Register.YL}


@dataclasses.dataclass(frozen=True)
class Memory:
    loc: Pointer | int

    @property
    def reads(self) -> set[Location]:
        if isinstance(self.loc, Pointer):
            return {*self.loc.reads, self}
        return {self}

    @property
    def writes(self) -> set[Location]:
        return {self}


X = Pointer("X")
Y = Pointer("Y")

MX = Memory(X)
MY = Memory(Y)

Location = Register | Flag | Memory | Pointer


@dataclasses.dataclass
class Imm4:
    value: int


@dataclasses.dataclass
class Imm8:
    value: int


Operand = Location | Imm4 | Imm8


def is_location(operand: Operand) -> TypeIs[Location]:
    return not isinstance(operand, (Imm4, Imm8))


class Operator(enum.Enum):
    ADC = "ADC"
    ADD = "ADD"
    AND = "AND"
    CP = "CP"
    DEC = "DEC"
    INC = "INC"
    HALT = "HALT"
    FAN = "FAN"
    LD = "LD"
    NOP = "NOP"
    OR = "OR"
    POP = "POP"
    PUSH = "PUSH"
    RLC = "RLC"
    RRC = "RRC"
    RST = "RST"
    XOR = "XOR"
    SBC = "SBC"
    SET = "SET"
    SLP = "SLP"
    SUB = "SUB"


NO_LOCATIONS: set[Location] = set()


@dataclasses.dataclass
class Operation:
    op: Operator
    args: list[Operand]

    def __init__(self, op: Operator, *args: Operand) -> None:
        self.op = op
        self.args = list(args)

    @property
    def reads(self) -> set[Location]:
        match self.op:
            case Operator.ADC | Operator.SBC:
                return {Flag.C, Flag.D, *self._arg_reads()}
            case Operator.RLC | Operator.RRC:
                return {Flag.C, *self._arg_reads()}
            case (
                Operator.HALT
                | Operator.POP
                | Operator.RST
                | Operator.SET
                | Operator.SLP
            ):
                return NO_LOCATIONS
            case Operator.LD:
                dst = self.args[0]
                src = self.args[1]
                dst_reads = NO_LOCATIONS
                src_reads = NO_LOCATIONS
                if isinstance(dst, Memory) and isinstance(dst.loc, Pointer):
                    dst_reads = dst.loc.reads
                if is_location(src):
                    src_reads = src.reads
                return dst_reads | src_reads
            case Operator.ADD | Operator.SUB:
                return {Flag.D, *self._arg_reads()}
            case (
                Operator.AND
                | Operator.CP
                | Operator.DEC
                | Operator.INC
                | Operator.FAN
                | Operator.OR
                | Operator.NOP
                | Operator.PUSH
                | Operator.XOR
            ):
                return self._arg_reads()

    @property
    def writes(self) -> set[Location]:
        match self.op:
            case Operator.ADC | Operator.ADD | Operator.SUB | Operator.SBC:
                dst = self.args[0]
                assert is_location(dst)
                return {Flag.C, Flag.Z, *dst.writes}
            case Operator.CP:
                return {Flag.C, Flag.Z}
            case Operator.FAN:
                return {Flag.Z}
            case Operator.RLC | Operator.RRC:
                dst = self.args[0]
                assert is_location(dst)
                return {Flag.C, *dst.writes}
            case Operator.AND | Operator.OR | Operator.XOR:
                dst = self.args[0]
                assert is_location(dst)
                return {Flag.Z, *dst.writes}
            case Operator.HALT | Operator.NOP | Operator.PUSH | Operator.SLP:
                return NO_LOCATIONS
            case Operator.DEC | Operator.INC:
                dst = self.args[0]
                if isinstance(dst, Pointer):
                    return dst.writes - {Register.XP, Register.YP}
                assert isinstance(dst, Memory) and isinstance(dst.loc, int)
                return {Flag.C, Flag.Z, *dst.writes}
            case Operator.POP | Operator.LD:
                dst = self.args[0]
                assert is_location(dst)
                return dst.writes
            case Operator.RST:
                flags = self.args[0]
                assert isinstance(flags, Imm4)
                return set(flag for flag in Flag if not (flags.value & flag.mask))
            case Operator.SET:
                flags = self.args[0]
                assert isinstance(flags, Imm4)
                return set(flag for flag in Flag if flags.value & flag.mask)

    def _arg_reads(self) -> set[Location]:
        locs: set[Location] = set()
        for oper in self.args:
            if is_location(oper):
                locs.update(oper.reads)
        return locs


@dataclasses.dataclass
class Call:
    target: memory.Address


Insn = Operation | Call


@dataclasses.dataclass
class Jump:
    target: memory.Address


@dataclasses.dataclass
class CondJump:
    flag: Flag
    negate: bool
    target: memory.Address
    fallthrough: memory.Address


@dataclasses.dataclass
class Return:
    offset: int = dataclasses.field(default=0)


@dataclasses.dataclass
class Dispatch:
    targets: list[memory.Address]


Terminator = Jump | CondJump | Return | Dispatch


@dataclasses.dataclass
class Block:
    start: memory.Address
    insns: list[Insn]
    terminator: Terminator
