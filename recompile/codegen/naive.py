from recompile.e0c6200 import disasm, memory
from recompile.ir import lift, ir


class UnsupportedInstructionError(Exception):
    def __init__(self, insn: ir.Insn) -> None:
        super().__init__(str(insn))


def generate(program: lift.Program) -> list[str]:
    out: list[str] = [
        'INCLUDE "prologue.inc"',
        "",
    ]
    for block in program.blocks.values():
        out.extend(generate_block(block))
    return out


def ld_a_operand(o: ir.Operand) -> list[str]:
    match o:
        case ir.Imm4(v) | ir.Imm8(v):
            return [f"LD A, ${v:X}"]
        case (
            ir.Register.A
            | ir.Register.B
            | ir.Register.F
            | ir.Register.XP
            | ir.Register.YP
        ):
            return [f"LD A, [h{o.value}]"]
        case ir.Register.XH | ir.Register.YH:
            return [
                f"LD A, [h{ir.ptr_base(o)}HL]",
                f"SWAP A",
                f"AND $f",
            ]
        case ir.Register.XL | ir.Register.YL:
            return [
                f"LD A, [h{ir.ptr_base(o)}HL]",
                f"AND $f",
            ]
        case ir.Memory(ptr):
            if isinstance(ptr, int):
                return [f"LD A, [wRAM+${ptr:X}]"]
            else:
                name = ptr.loc
                return [
                    f"LD A, [h{name}P]",
                    f"LD H, A",
                    f"LD A, [h{name}HL]",
                    f"LD L, A",
                    f"LD BC, wRAM",
                    f"ADD HL, BC",
                    f"LD A, [HL]",
                ]
        case _:
            raise ValueError(f"invalid operand {o}")


def ld_loc_a(l: ir.Location) -> list[str]:
    match l:
        case (
            ir.Register.A
            | ir.Register.B
            | ir.Register.F
            | ir.Register.XP
            | ir.Register.YP
        ):
            return [f"LD [h{l.value}], A"]
        case ir.Register.XH | ir.Register.YH:
            return [
                f"LD B, A",
                f"LD A, [h{ir.ptr_base(l)}HL]",
                f"SWAP A",
                f"AND $f0",
                f"ADD B",
                f"SWAP A",
                f"LD [h{ir.ptr_base(l)}HL], A",
            ]
        case ir.Register.XL | ir.Register.YL:
            return [
                f"LD B, A",
                f"LD A, [h{ir.ptr_base(l)}HL]",
                f"AND $f0",
                f"ADD B",
                f"LD [h{ir.ptr_base(l)}HL], A",
            ]
        case ir.Memory(ptr):
            if isinstance(ptr, int):
                return [f"LD [wRAM+${ptr:X}], A"]
            else:
                name = ptr.loc
                return [
                    f"LD D, A",
                    f"LD A, [h{name}P]",
                    f"LD H, A",
                    f"LD A, [h{name}HL]",
                    f"LD L, A",
                    f"LD BC, wRAM",
                    f"ADD HL, BC",
                    f"LD [HL], D",
                ]
        case _:
            raise ValueError(f"invalid location {l}")


def generate_block(block: ir.Block) -> list[str]:
    lines: list[str] = []
    for insn in block.insns:
        if isinstance(insn, ir.Call):
            lines.append(f"CALL {_address(insn.target)}")
            # NB: Conditional jump needed after call to correctly handle
            # distinction between RET and RETS
            lines.append(f"JP C, {_address(insn.addr.next().next())}")
            continue
        elif isinstance(insn, ir.Marker):
            lines.append(f"{_address(insn.addr)}:")
            lines.append(f"; {disasm.render_insn(insn.raw)}")
            continue
        match insn.op:
            case ir.Operator.ADC:
                lines.extend(ld_a_operand(insn.args[0]))
                lines.append("LD E, A")
                lines.extend(ld_a_operand(insn.args[1]))
                lines.extend(
                    [
                        "ADD E",
                        "LD HL, hF",
                        "BIT 0, [HL]",
                        "JR Z, .skipAdd",
                        "INC A",
                        ".skipAdd:",
                        "RES 0, [HL]",
                        "RES 1, [HL]",
                        "BIT 4, A",
                        "JR Z, .skipC",
                        "SET 0, [HL]",
                        ".skipC:",
                        "AND $f",
                        "JR NZ, .done",
                        "SET 1, [HL]",
                        ".done:",
                    ]
                )
                assert ir.is_location(insn.args[0])
                lines.extend(ld_loc_a(insn.args[0]))
            case ir.Operator.ADD:
                lines.extend(ld_a_operand(insn.args[0]))
                lines.append("LD E, A")
                lines.extend(ld_a_operand(insn.args[1]))
                lines.extend(
                    [
                        "ADD E",
                        "LD HL, hF",
                        "RES 0, [HL]",
                        "RES 1, [HL]",
                        "BIT 4, A",
                        "JR Z, .skipC",
                        "SET 0, [HL]",
                        ".skipC:",
                        "AND $f",
                        "JR NZ, .done",
                        "SET 1, [HL]",
                        ".done:",
                    ]
                )
                assert ir.is_location(insn.args[0])
                lines.extend(ld_loc_a(insn.args[0]))
            case ir.Operator.AND:
                lines.extend(ld_a_operand(insn.args[0]))
                lines.append("LD E, A")
                lines.extend(ld_a_operand(insn.args[1]))
                lines.extend(
                    [
                        "AND E",
                        "LD HL, hF",
                        "RES 1, [HL]",
                        "JR NZ, .done",
                        "SET 1, [HL]",
                        ".done:",
                    ]
                )
                assert ir.is_location(insn.args[0])
                lines.extend(ld_loc_a(insn.args[0]))
            case ir.Operator.CP:
                lines.extend(ld_a_operand(insn.args[1]))
                lines.append("LD E, A")
                lines.extend(ld_a_operand(insn.args[0]))
                lines.extend(
                    [
                        "CP E",
                        "LD HL, hF",
                        "RES 0, [HL]",
                        "RES 1, [HL]",
                        "JR NC, .skipC",
                        "SET 0, [HL]",
                        ".skipC:",
                        "JR NZ, .done",
                        "SET 1, [HL]",
                        ".done:",
                    ]
                )
            case ir.Operator.FAN:
                lines.extend(ld_a_operand(insn.args[0]))
                lines.append("LD E, A")
                lines.extend(ld_a_operand(insn.args[1]))
                lines.extend(
                    [
                        "AND E",
                        "LD HL, hF",
                        "RES 1, [HL]",
                        "JR NZ, .done",
                        "SET 1, [HL]",
                        ".done:",
                    ]
                )
            case ir.Operator.HALT:
                lines.append("; TODO: Interrupt handling")
            case ir.Operator.INC:
                match insn.args[0]:
                    case ir.X:
                        lines.append("LD HL, hXHL")
                        lines.append("INC [HL]")
                    case ir.Y:
                        lines.append("LD HL, hYHL")
                        lines.append("INC [HL]")
                    case _:
                        raise UnsupportedInstructionError(insn)
            case ir.Operator.LD:
                lines.extend(ld_a_operand(insn.args[1]))
                assert ir.is_location(insn.args[0])
                lines.extend(ld_loc_a(insn.args[0]))
            case ir.Operator.NOP:
                lines.append("NOP")
            case ir.Operator.OR:
                lines.extend(ld_a_operand(insn.args[0]))
                lines.append("LD E, A")
                lines.extend(ld_a_operand(insn.args[1]))
                lines.extend(
                    [
                        "OR E",
                        "LD HL, hF",
                        "RES 1, [HL]",
                        "JR NZ, .done",
                        "SET 1, [HL]",
                        ".done:",
                    ]
                )
                assert ir.is_location(insn.args[0])
                lines.extend(ld_loc_a(insn.args[0]))
            case ir.Operator.POP:
                assert isinstance(insn.args[0], ir.Register)
                lines.extend(
                    [
                        "LD HL, SP + 0",
                        "LD A, [HL+]",
                        "LD SP, HL",
                    ]
                )
                lines.extend(ld_loc_a(insn.args[0]))
            case ir.Operator.PUSH:
                assert isinstance(insn.args[0], ir.Register)
                lines.extend(ld_a_operand(insn.args[0]))
                lines.append(f"LD HL, SP + 0")
                lines.append(f"LD [HL-], A")
                lines.append(f"LD SP, HL")
            case ir.Operator.RLC:
                lines.extend(ld_a_operand(insn.args[0]))
                lines.extend(
                    [
                        "SLA A",
                        "LD HL, hF",
                        "BIT 0, [HL]",
                        "JR Z, .skipOr",
                        "OR 1",
                        ".skipOr:",
                        "RES 0, [HL]",
                        "BIT 4, A",
                        "JR Z, .skipCarry",
                        "SET 0, [HL]",
                        ".skipCarry:",
                        "AND $f",
                    ]
                )
                assert ir.is_location(insn.args[0])
                lines.extend(ld_loc_a(insn.args[0]))
            case ir.Operator.RRC:
                lines.extend(ld_a_operand(insn.args[0]))
                lines.extend(
                    [
                        "LD HL, hF",
                        "BIT 0, [HL]",
                        "JR Z, .skipOr",
                        "OR $10",
                        ".skipOr:",
                        "SRA A",
                        "RES 0, [HL]",
                        "JR NC, .skipCarry",
                        "SET 0, [HL]",
                        ".skipCarry:",
                    ]
                )
                assert ir.is_location(insn.args[0])
                lines.extend(ld_loc_a(insn.args[0]))
            case ir.Operator.RST:
                assert isinstance(insn.args[0], ir.Imm4)
                lines.append(f"LD A, [hF]")
                lines.append(f"AND ${insn.args[0].value:X}")
                lines.append(f"LD [hF], A")
            case ir.Operator.SBC:
                lines.extend(ld_a_operand(insn.args[1]))
                lines.append("LD E, A")
                lines.extend(ld_a_operand(insn.args[0]))
                lines.extend(
                    [
                        "LD HL, hF",
                        "BIT 0, [HL]",
                        "JR Z, .subtract",
                        "INC E",
                        ".subtract:",
                        "SUB E",
                        "RES 0, [HL]",
                        "RES 1, [HL]",
                        "JR NC, .noCarry",
                        "SET 0, [HL]",
                        ".noCarry:",
                        "AND $f",
                        "JR NZ, .done",
                        "SET 1, [HL]",
                        ".done:",
                    ]
                )
                assert ir.is_location(insn.args[0])
                lines.extend(ld_loc_a(insn.args[0]))
            case ir.Operator.SET:
                assert isinstance(insn.args[0], ir.Imm4)
                lines.append(f"LD A, [hF]")
                lines.append(f"OR ${insn.args[0].value:X}")
                lines.append(f"LD [hF], A")
            case ir.Operator.SUB:
                lines.extend(ld_a_operand(insn.args[1]))
                lines.append("LD E, A")
                lines.extend(ld_a_operand(insn.args[0]))
                lines.extend(
                    [
                        "SUB E",
                        "LD HL, hF",
                        "RES 0, [HL]",
                        "RES 1, [HL]",
                        "JR NC, .noCarry",
                        "SET 0, [HL]",
                        ".noCarry:",
                        "JR NZ, .done",
                        "SET 1, [HL]",
                        ".done:",
                        "AND $f",
                    ]
                )
                assert ir.is_location(insn.args[0])
                lines.extend(ld_loc_a(insn.args[0]))
            case ir.Operator.XOR:
                lines.extend(ld_a_operand(insn.args[0]))
                lines.append("LD E, A")
                lines.extend(ld_a_operand(insn.args[1]))
                lines.extend(
                    [
                        "XOR E",
                        "LD HL, hF",
                        "RES 1, [HL]",
                        "JR NZ, .skipZ",
                        "SET 1, [HL]",
                        ".skipZ:",
                    ]
                )
                assert ir.is_location(insn.args[0])
                lines.extend(ld_loc_a(insn.args[0]))
            case _:
                raise UnsupportedInstructionError(insn)
    match block.terminator:
        case ir.Jump(target):
            lines.append(f"JP {_address(target)}")
        case ir.Return(offset):
            # NB: We set the carry flag if we are generating a RETS instruction
            # so that the call site knows to skip the instruction after it
            if offset == 0:
                lines.append("OR A")
            elif offset == 1:
                lines.append("SCF")
            else:
                raise ValueError(f"unsupported {offset=} in return")
            lines.append("RET")
        case ir.CondJump(flag, negate, target, fallthrough):
            if flag == ir.Flag.C:
                flag_bit = 0
            elif flag == ir.Flag.Z:
                flag_bit = 1
            else:
                raise ValueError(f"unsupported flag {flag} in conditional jump")
            lines.extend(
                [
                    f"LD A, [hF]",
                    f"BIT {flag_bit}, A",
                    (
                        f"JP Z, {_address(target)}"
                        if negate
                        else f"JP NZ, {_address(target)}"
                    ),
                    f"JP {_address(fallthrough)}",
                ]
            )
        case ir.Dispatch(table):
            lines.extend(
                [
                    "LD A, [hB]",
                    "SWAP A",
                    "LD B, A",
                    "LD A, [hA]",
                    "OR B",
                    f"SUB {table.addr.step}",
                    "LD HL, .jump_table",
                    "LD B, 0",
                    "LD C, A",
                    "ADD HL, BC",
                    "ADD HL, BC",
                    "ADD HL, BC",
                    "JP HL",
                ]
            )
            lines.append(".jump_table:")
            entry_addr = table.addr
            for _ in range(table.count):
                lines.append(f"JP {_address(entry_addr)}")
                entry_addr = entry_addr.next()
                for _ in range(table.stride - 1):
                    lines.append(f"JP $0000 ; STUB")
                    entry_addr = entry_addr.next()
    lines.append("")
    return [line if line.endswith(":") else f"\t{line}" for line in lines]


def _address(addr: memory.Address) -> str:
    return f"rom_{addr.bank}_{addr.page:X}_{addr.step:02X}"
