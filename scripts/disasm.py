import argparse

from recompile.e0c6200 import insn, memory


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
        insn_str = render_insn(addr, insn.parse(rom.at(addr)))
        print(insn_str)


RQ_NAMES = ["A", "B", "MX", "MY"]


def hex4(imm: int) -> str:
    return f"{imm:01X}H"


def hex8(imm: int) -> str:
    return f"{imm:02X}H"


def hex5(imm: int) -> str:
    return f"{imm:02X}H"


def render_insn(addr: memory.Address, ins: insn.Insn) -> str:
    addr_str = f"{addr.bank}:{addr.page:x}:{addr.step:02x}"
    match ins:
        case insn.ACPX_MX_R(r):
            insn_str = f"ACPX MX, {RQ_NAMES[r]}"
        case insn.ACPY_MY_R(r):
            insn_str = f"ACPY MY, {RQ_NAMES[r]}"
        case insn.ADC_R_I(r, i):
            insn_str = f"ADC {RQ_NAMES[r]}, {hex4(i)}"
        case insn.ADC_R_Q(r, q):
            insn_str = f"ADC {RQ_NAMES[r]}, {RQ_NAMES[q]}"
        case insn.ADC_XH_I(i):
            insn_str = f"ADC XH, {hex4(i)}"
        case insn.ADC_XL_I(i):
            insn_str = f"ADC XL, {hex4(i)}"
        case insn.ADC_YH_I(i):
            insn_str = f"ADC YH, {hex4(i)}"
        case insn.ADC_YL_I(i):
            insn_str = f"ADC YL, {hex4(i)}"
        case insn.ADD_R_I(r, i):
            insn_str = f"ADD {RQ_NAMES[r]}, {hex4(i)}"
        case insn.ADD_R_Q(r, q):
            insn_str = f"ADD {RQ_NAMES[r]}, {RQ_NAMES[q]}"
        case insn.AND_R_I(r, i):
            insn_str = f"AND {RQ_NAMES[r]}, {hex4(i)}"
        case insn.AND_R_Q(r, q):
            insn_str = f"AND {RQ_NAMES[r]}, {RQ_NAMES[q]}"
        case insn.CALL(step):
            insn_str = f"CALL {hex8(step)}"
        case insn.CALZ(step):
            insn_str = f"CALZ {hex8(step)}"
        case insn.CP_R_I(r, i):
            insn_str = f"CP {RQ_NAMES[r]}, {hex4(i)}"
        case insn.CP_R_Q(r, q):
            insn_str = f"CP {RQ_NAMES[r]}, {RQ_NAMES[q]}"
        case insn.CP_XH_I(i):
            insn_str = f"CP XH, {hex4(i)}"
        case insn.CP_XL_I(i):
            insn_str = f"CP XL, {hex4(i)}"
        case insn.CP_YH_I(i):
            insn_str = f"CP YH, {hex4(i)}"
        case insn.CP_YL_I(i):
            insn_str = f"CP YL, {hex4(i)}"
        case insn.DEC_MN(n):
            insn_str = f"DEC M({hex4(n)})"
        case insn.DEC_SP():
            insn_str = "DEC SP"
        case insn.FAN_R_I(r, i):
            insn_str = f"FAN {RQ_NAMES[r]}, {hex4(i)}"
        case insn.FAN_R_Q(r, q):
            insn_str = f"FAN {RQ_NAMES[r]}, {RQ_NAMES[q]}"
        case insn.HALT():
            insn_str = "HALT"
        case insn.INC_MN(n):
            insn_str = f"INC M({hex4(n)})"
        case insn.INC_SP():
            insn_str = "INC SP"
        case insn.JP(step):
            insn_str = f"JP {hex8(step)}"
        case insn.JPBA():
            insn_str = "JPBA"
        case insn.JP_COND(step, c):
            insn_str = f"JP {c.value}, {hex8(step)}"
        case insn.LBPX_MX_E(e):
            insn_str = f"LBPX MX, {hex8(e)}"
        case insn.LDPX_MX_I(i):
            insn_str = f"LDPX MX, {hex4(i)}"
        case insn.LDPX_R_Q(r, q):
            insn_str = f"LDPX {RQ_NAMES[r]}, {RQ_NAMES[q]}"
        case insn.LDPY_MY_I(i):
            insn_str = f"LDPY MY, {hex4(i)}"
        case insn.LDPY_R_Q(r, q):
            insn_str = f"LDPY {RQ_NAMES[r]}, {RQ_NAMES[q]}"
        case insn.LD_A_MN(n):
            insn_str = f"LD A, M({hex4(n)})"
        case insn.LD_B_MN(n):
            insn_str = f"LD B, M({hex4(n)})"
        case insn.LD_MN_A(n):
            insn_str = f"LD M({hex4(n)}), A"
        case insn.LD_MN_B(n):
            insn_str = f"LD M({hex4(n)}), B"
        case insn.LD_R_I(r, i):
            insn_str = f"LD {RQ_NAMES[r]}, {hex4(i)}"
        case insn.LD_R_Q(r, q):
            insn_str = f"LD {RQ_NAMES[r]}, {RQ_NAMES[q]}"
        case insn.LD_R_SPH(r):
            insn_str = f"LD {RQ_NAMES[r]}, SPH"
        case insn.LD_R_SPL(r):
            insn_str = f"LD {RQ_NAMES[r]}, SPL"
        case insn.LD_R_XH(r):
            insn_str = f"LD {RQ_NAMES[r]}, XH"
        case insn.LD_R_XL(r):
            insn_str = f"LD {RQ_NAMES[r]}, XL"
        case insn.LD_R_XP(r):
            insn_str = f"LD {RQ_NAMES[r]}, XP"
        case insn.LD_R_YH(r):
            insn_str = f"LD {RQ_NAMES[r]}, YH"
        case insn.LD_R_YL(r):
            insn_str = f"LD {RQ_NAMES[r]}, YL"
        case insn.LD_R_YP(r):
            insn_str = f"LD {RQ_NAMES[r]}, YP"
        case insn.LD_SPH_R(r):
            insn_str = f"LD SPH, {RQ_NAMES[r]}"
        case insn.LD_SPL_R(r):
            insn_str = f"LD SPL, {RQ_NAMES[r]}"
        case insn.LD_XH_R(r):
            insn_str = f"LD XH, {RQ_NAMES[r]}"
        case insn.LD_XL_R(r):
            insn_str = f"LD XL, {RQ_NAMES[r]}"
        case insn.LD_XP_R(r):
            insn_str = f"LD XP, {RQ_NAMES[r]}"
        case insn.LD_X_E(e):
            insn_str = f"LD X, {hex8(e)}"
        case insn.LD_YH_R(r):
            insn_str = f"LD YH, {RQ_NAMES[r]}"
        case insn.LD_YL_R(r):
            insn_str = f"LD YL, {RQ_NAMES[r]}"
        case insn.LD_YP_R(r):
            insn_str = f"LD YP, {RQ_NAMES[r]}"
        case insn.LD_Y_E(e):
            insn_str = f"LD Y, {hex8(e)}"
        case insn.NOP5():
            insn_str = "NOP5"
        case insn.NOP7():
            insn_str = "NOP7"
        case insn.OR_R_I(r, i):
            insn_str = f"OR {RQ_NAMES[r]}, {hex4(i)}"
        case insn.OR_R_Q(r, q):
            insn_str = f"OR {RQ_NAMES[r]}, {RQ_NAMES[q]}"
        case insn.POP_F():
            insn_str = "POP F"
        case insn.POP_R(r):
            insn_str = f"POP {RQ_NAMES[r]}"
        case insn.POP_XH():
            insn_str = "POP XH"
        case insn.POP_XL():
            insn_str = "POP XL"
        case insn.POP_XP():
            insn_str = "POP XP"
        case insn.POP_YH():
            insn_str = "POP YH"
        case insn.POP_YL():
            insn_str = "POP YL"
        case insn.POP_YP():
            insn_str = "POP YP"
        case insn.PSET(p):
            insn_str = f"PSET {hex5(p)}"
        case insn.PUSH_F():
            insn_str = "PUSH F"
        case insn.PUSH_R(r):
            insn_str = f"PUSH {RQ_NAMES[r]}"
        case insn.PUSH_XH():
            insn_str = "PUSH XH"
        case insn.PUSH_XL():
            insn_str = "PUSH XL"
        case insn.PUSH_XP():
            insn_str = "PUSH XP"
        case insn.PUSH_YH():
            insn_str = "PUSH YH"
        case insn.PUSH_YL():
            insn_str = "PUSH YL"
        case insn.PUSH_YP():
            insn_str = "PUSH YP"
        case insn.RET():
            insn_str = "RET"
        case insn.RETD(e):
            insn_str = f"RETD {hex8(e)}"
        case insn.RETS():
            insn_str = "RETS"
        case insn.RLC(r):
            insn_str = f"RLC {RQ_NAMES[r]}"
        case insn.RRC(r):
            insn_str = f"RRC {RQ_NAMES[r]}"
        case insn.RST(i):
            match i:
                case 7:
                    insn_str = "DI"
                case 0xB:
                    insn_str = "RDF"
                case 0xD:
                    insn_str = "RZF"
                case 0xE:
                    insn_str = "RCF"
                case _:
                    insn_str = f"RST F, {hex4(i)}"
        case insn.SBC_R_I(r, i):
            insn_str = f"SBC {RQ_NAMES[r]}, {hex4(i)}"
        case insn.SBC_R_Q(r, q):
            insn_str = f"SBC {RQ_NAMES[r]}, {RQ_NAMES[q]}"
        case insn.SCPX_MX_R(r):
            insn_str = f"SCPX MX, {RQ_NAMES[r]}"
        case insn.SCPY_MY_R(r):
            insn_str = f"SCPY MY, {RQ_NAMES[r]}"
        case insn.SET(i):
            match i:
                case 1:
                    insn_str = "SCF"
                case 2:
                    insn_str = "SZF"
                case 4:
                    insn_str = "SDF"
                case 8:
                    insn_str = "EI"
                case _:
                    insn_str = f"SET F, {hex4(i)}"
        case insn.SLP():
            insn_str = "SLP"
        case insn.SUB_R_Q(r, q):
            insn_str = f"SUB {RQ_NAMES[r]}, {RQ_NAMES[q]}"
        case insn.XOR_R_I(r, i):
            insn_str = f"XOR {RQ_NAMES[r]}, {hex4(i)}"
        case insn.XOR_R_Q(r, q):
            insn_str = f"XOR {RQ_NAMES[r]}, {RQ_NAMES[q]}"
        case _:
            raise ValueError(f"unsupported instruction {ins}")
    return f"{addr_str}\t{insn_str}"


if __name__ == "__main__":
    main()
