from typing import Optional

from recompile.e0c6200 import cfg, indirect, insn, memory
from recompile.ir import ir

R_OPERANDS: dict[int, ir.Operand] = {
    0: ir.Register.A,
    1: ir.Register.B,
    2: ir.MX,
    3: ir.MY,
}

COND_FLAGS: dict[insn.FlagCondition, tuple[ir.Flag, bool]] = {
    insn.FlagCondition.CARRY: (ir.Flag.C, False),
    insn.FlagCondition.NOT_CARRY: (ir.Flag.C, True),
    insn.FlagCondition.ZERO: (ir.Flag.Z, False),
    insn.FlagCondition.NOT_ZERO: (ir.Flag.Z, True),
}


def blocks(rom: memory.ROM, cfg_blocks: cfg.Blocks) -> dict[memory.Address, ir.Block]:
    out: dict[memory.Address, ir.Block] = {}
    for start, cfg_block in cfg_blocks.blocks.items():
        out[start] = block(rom, cfg_blocks.targets, cfg_blocks.leaders, cfg_block)
    return out


def block(
    rom: memory.ROM,
    targets: indirect.IndirectTargets,
    leaders: set[memory.Address],
    cfg_block: cfg.Block,
) -> ir.Block:
    insns: list[ir.Insn] = []
    terminator: Optional[ir.Terminator] = None
    call_index = 0

    addr = cfg_block.start
    while True:
        ins = insn.parse(rom.at(addr))
        match ins:
            case insn.ACPX_MX_R(r):
                insns.append(ir.Operation(ir.Operator.ADC, ir.MX, R_OPERANDS[r]))
                insns.append(ir.Operation(ir.Operator.INC, ir.X))
            case insn.ACPY_MY_R(r):
                insns.append(ir.Operation(ir.Operator.ADC, ir.MY, R_OPERANDS[r]))
                insns.append(ir.Operation(ir.Operator.INC, ir.Y))
            case insn.ADC_XH_I(i):
                insns.append(ir.Operation(ir.Operator.ADC, ir.Register.XH, ir.Imm4(i)))
            case insn.ADC_XL_I(i):
                insns.append(ir.Operation(ir.Operator.ADC, ir.Register.XL, ir.Imm4(i)))
            case insn.ADC_YH_I(i):
                insns.append(ir.Operation(ir.Operator.ADC, ir.Register.YH, ir.Imm4(i)))
            case insn.ADC_YL_I(i):
                insns.append(ir.Operation(ir.Operator.ADC, ir.Register.YL, ir.Imm4(i)))
            case insn.ADC_R_I(r, i):
                insns.append(_op_r_i(ir.Operator.ADC, r, i))
            case insn.ADD_R_I(r, i):
                insns.append(_op_r_i(ir.Operator.ADD, r, i))
            case insn.ADD_R_Q(r, q):
                insns.append(_op_r_q(ir.Operator.ADD, r, q))
            case insn.AND_R_I(r, i):
                insns.append(_op_r_i(ir.Operator.AND, r, i))
            case insn.CALL() | insn.CALZ():
                insns.append(ir.Call(cfg_block.calls[call_index]))
                call_index += 1
            case insn.CP_R_I(r, i):
                insns.append(_op_r_i(ir.Operator.CP, r, i))
            case insn.CP_R_Q(r, q):
                insns.append(_op_r_q(ir.Operator.CP, r, q))
            case insn.CP_XH_I(i):
                insns.append(ir.Operation(ir.Operator.CP, ir.Register.XH, ir.Imm4(i)))
            case insn.CP_XL_I(i):
                insns.append(ir.Operation(ir.Operator.CP, ir.Register.XL, ir.Imm4(i)))
            case insn.CP_YH_I(i):
                insns.append(ir.Operation(ir.Operator.CP, ir.Register.YH, ir.Imm4(i)))
            case insn.CP_YL_I(i):
                insns.append(ir.Operation(ir.Operator.CP, ir.Register.YL, ir.Imm4(i)))
            case insn.FAN_R_I(r, i):
                insns.append(_op_r_i(ir.Operator.FAN, r, i))
            case insn.FAN_R_Q(r, q):
                insns.append(_op_r_q(ir.Operator.FAN, r, q))
            case insn.HALT():
                insns.append(ir.Operation(ir.Operator.HALT))
            case insn.JP():
                assert len(cfg_block.successors) == 1
                terminator = ir.Jump(target=cfg_block.successors[0])
                break
            case insn.JPBA():
                match targets[addr]:
                    case indirect.ReturnTable():
                        terminator = ir.Return()
                    case indirect.DispatchTable():
                        terminator = ir.Dispatch(cfg_block.successors)
                break
            case insn.JP_COND(_step, cond):
                assert len(cfg_block.successors) == 2
                flag, negate = COND_FLAGS[cond]
                terminator = ir.CondJump(
                    flag=flag,
                    negate=negate,
                    target=cfg_block.successors[0],
                    fallthrough=cfg_block.successors[1],
                )
                break
            case insn.LBPX_MX_E(e):
                insns.append(ir.Operation(ir.Operator.LD, ir.MX, ir.Imm4(e & 0xF)))
                insns.append(ir.Operation(ir.Operator.INC, ir.X))
                insns.append(ir.Operation(ir.Operator.LD, ir.MX, ir.Imm4(e >> 4)))
                insns.append(ir.Operation(ir.Operator.INC, ir.X))
            case insn.LDPX_MX_I(i):
                insns.append(ir.Operation(ir.Operator.LD, ir.MX, ir.Imm4(i)))
                insns.append(ir.Operation(ir.Operator.INC, ir.X))
            case insn.LDPX_R_Q(r, q):
                insns.append(_op_r_q(ir.Operator.LD, r, q))
                insns.append(ir.Operation(ir.Operator.INC, ir.X))
            case insn.LDPY_MY_I(i):
                insns.append(ir.Operation(ir.Operator.LD, ir.MY, ir.Imm4(i)))
                insns.append(ir.Operation(ir.Operator.INC, ir.Y))
            case insn.LDPY_R_Q(r, q):
                insns.append(_op_r_q(ir.Operator.LD, r, q))
                insns.append(ir.Operation(ir.Operator.INC, ir.Y))
            case insn.LD_A_MN(n):
                insns.append(ir.Operation(ir.Operator.LD, ir.Register.A, ir.Memory(n)))
            case insn.LD_B_MN(n):
                insns.append(ir.Operation(ir.Operator.LD, ir.Register.B, ir.Memory(n)))
            case insn.LD_MN_A(n):
                insns.append(ir.Operation(ir.Operator.LD, ir.Memory(n), ir.Register.A))
            case insn.LD_MN_B(n):
                insns.append(ir.Operation(ir.Operator.LD, ir.Memory(n), ir.Register.B))
            case insn.LD_R_I(r, i):
                insns.append(_op_r_i(ir.Operator.LD, r, i))
            case insn.LD_R_Q(r, q):
                insns.append(_op_r_q(ir.Operator.LD, r, q))
            case insn.LD_R_XH(r):
                insns.append(
                    ir.Operation(ir.Operator.LD, R_OPERANDS[r], ir.Register.XH)
                )
            case insn.LD_R_XL(r):
                insns.append(
                    ir.Operation(ir.Operator.LD, R_OPERANDS[r], ir.Register.XL)
                )
            case insn.LD_R_XP(r):
                insns.append(
                    ir.Operation(ir.Operator.LD, R_OPERANDS[r], ir.Register.XP)
                )
            case insn.LD_SPL_R() | insn.LD_SPH_R():
                pass
            case insn.LD_X_E(e):
                insns.append(
                    ir.Operation(ir.Operator.LD, ir.Register.XH, ir.Imm4(e >> 4))
                )
                insns.append(
                    ir.Operation(ir.Operator.LD, ir.Register.XL, ir.Imm4(e & 0xF))
                )
            case insn.LD_XH_R(r):
                insns.append(
                    ir.Operation(ir.Operator.LD, ir.Register.XH, R_OPERANDS[r])
                )
            case insn.LD_XL_R(r):
                insns.append(
                    ir.Operation(ir.Operator.LD, ir.Register.XL, R_OPERANDS[r])
                )
            case insn.LD_XP_R(r):
                insns.append(
                    ir.Operation(ir.Operator.LD, ir.Register.XP, R_OPERANDS[r])
                )
            case insn.LD_Y_E(e):
                insns.append(
                    ir.Operation(ir.Operator.LD, ir.Register.YH, ir.Imm4(e >> 4))
                )
                insns.append(
                    ir.Operation(ir.Operator.LD, ir.Register.YL, ir.Imm4(e & 0xF))
                )
            case insn.LD_YH_R(r):
                insns.append(
                    ir.Operation(ir.Operator.LD, ir.Register.YH, R_OPERANDS[r])
                )
            case insn.LD_YL_R(r):
                insns.append(
                    ir.Operation(ir.Operator.LD, ir.Register.YL, R_OPERANDS[r])
                )
            case insn.LD_YP_R(r):
                insns.append(
                    ir.Operation(ir.Operator.LD, ir.Register.YP, R_OPERANDS[r])
                )
            case insn.NOP5() | insn.NOP7():
                insns.append(ir.Operation(ir.Operator.NOP))
            case insn.OR_R_I(r, i):
                insns.append(_op_r_i(ir.Operator.OR, r, i))
            case insn.OR_R_Q(r, q):
                insns.append(_op_r_q(ir.Operator.OR, r, q))
            case insn.POP_F():
                insns.append(ir.Operation(ir.Operator.POP, ir.Register.F))
            case insn.POP_R(r):
                insns.append(ir.Operation(ir.Operator.POP, R_OPERANDS[r]))
            case insn.POP_XH():
                insns.append(ir.Operation(ir.Operator.POP, ir.Register.XH))
            case insn.POP_XL():
                insns.append(ir.Operation(ir.Operator.POP, ir.Register.XL))
            case insn.POP_XP():
                insns.append(ir.Operation(ir.Operator.POP, ir.Register.XP))
            case insn.POP_YH():
                insns.append(ir.Operation(ir.Operator.POP, ir.Register.YH))
            case insn.POP_YL():
                insns.append(ir.Operation(ir.Operator.POP, ir.Register.YL))
            case insn.POP_YP():
                insns.append(ir.Operation(ir.Operator.POP, ir.Register.YP))
            case insn.PSET():
                pass
            case insn.PUSH_F():
                insns.append(ir.Operation(ir.Operator.PUSH, ir.Register.F))
            case insn.PUSH_R(r):
                insns.append(ir.Operation(ir.Operator.PUSH, R_OPERANDS[r]))
            case insn.PUSH_XH():
                insns.append(ir.Operation(ir.Operator.PUSH, ir.Register.XH))
            case insn.PUSH_XL():
                insns.append(ir.Operation(ir.Operator.PUSH, ir.Register.XL))
            case insn.PUSH_XP():
                insns.append(ir.Operation(ir.Operator.PUSH, ir.Register.XP))
            case insn.PUSH_YH():
                insns.append(ir.Operation(ir.Operator.PUSH, ir.Register.YH))
            case insn.PUSH_YL():
                insns.append(ir.Operation(ir.Operator.PUSH, ir.Register.YL))
            case insn.PUSH_YP():
                insns.append(ir.Operation(ir.Operator.PUSH, ir.Register.YP))
            case insn.RLC(r):
                insns.append(ir.Operation(ir.Operator.RLC, R_OPERANDS[r]))
            case insn.RET():
                terminator = ir.Return()
                break
            case insn.RETD(e):
                insns.append(ir.Operation(ir.Operator.LD, ir.MX, ir.Imm4(e & 0xF)))
                insns.append(ir.Operation(ir.Operator.INC, ir.X))
                insns.append(ir.Operation(ir.Operator.LD, ir.MX, ir.Imm4(e >> 4)))
                insns.append(ir.Operation(ir.Operator.INC, ir.X))
                terminator = ir.Return()
                break
            case insn.RETS():
                terminator = ir.Return(offset=1)
                break
            case insn.RRC(r):
                insns.append(ir.Operation(ir.Operator.RRC, R_OPERANDS[r]))
            case insn.RST(f):
                insns.append(_op_i4(ir.Operator.RST, f))
            case insn.SBC_R_I(r, i):
                insns.append(_op_r_i(ir.Operator.SBC, r, i))
            case insn.SCPX_MX_R(r):
                insns.append(ir.Operation(ir.Operator.SBC, ir.MX, R_OPERANDS[r]))
                insns.append(ir.Operation(ir.Operator.INC, ir.X))
            case insn.SCPY_MY_R(r):
                insns.append(ir.Operation(ir.Operator.SBC, ir.MY, R_OPERANDS[r]))
                insns.append(ir.Operation(ir.Operator.INC, ir.Y))
            case insn.SET(f):
                insns.append(_op_i4(ir.Operator.SET, f))
            case insn.SUB_R_Q(r, q):
                insns.append(_op_r_q(ir.Operator.SUB, r, q))
            case insn.XOR_R_I(r, i):
                insns.append(_op_r_i(ir.Operator.XOR, r, i))
            case _:
                raise NotImplementedError(f"unsupported instruction: {ins}")
        addr = addr.next()
        if addr in leaders:
            terminator = ir.Jump(target=addr)
            break

    assert terminator is not None
    return ir.Block(
        start=cfg_block.start,
        insns=insns,
        terminator=terminator,
    )


def _op_i4(op: ir.Operator, i: int) -> ir.Operation:
    return ir.Operation(op, ir.Imm4(i))


def _op_r_i(op: ir.Operator, r: int, i: int) -> ir.Operation:
    return ir.Operation(op, R_OPERANDS[r], ir.Imm4(i))


def _op_r_q(op: ir.Operator, r: int, q: int) -> ir.Operation:
    return ir.Operation(op, R_OPERANDS[r], R_OPERANDS[q])
