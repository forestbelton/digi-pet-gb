INCLUDE "hardware.inc"
INCLUDE "macro.inc"

SECTION "Timer ISR", ROM0[$50]
    JP _handle_timer

SECTION "Header", ROM0[$100]
    JP _start

; NB: Leave space for cartridge header
DS $150 - @, 0

SECTION "Entrypoint", ROM0[$150]
_start:
    DI
    ; Initialize HRAM
    XOR A
    LDH [hBank], A
    LDH [hHALT], A
    LDH [hA], A
    LDH [hB], A
    LDH [hF], A
    LDH [hXP], A
    LDH [hXHL], A
    LDH [hYP], A
    LDH [hYHL], A
    LDH [hIO_CTRL_OSC], A
    LDH [hIO_TM], A
    LDH [hIO_IT], A
    LDH [hIO_EIT], A

    ; Initialize timer
    LD A, 240
    LDH [rTMA], A
    LD A, TAC_START | TAC_4KHZ
    LDH [rTAC], A

    ; Enable interrupts
    LD A, IE_TIMER
    LDH [rIE], A
    EI

    FAR_JUMP rom_0_1_00

SECTION "Utilities", ROM0

_handle_timer::
    PUSH AF
    PUSH BC
    PUSH DE
    PUSH HL
    ; NB: TM and IT advance whether or not the guest has interrupts enabled. The
    ; core latches IT on the falling edge of TM bits 2, 4, 6 and 7, which happens
    ; exactly when the low 3, 5, 7 or 8 bits of the incremented count are zero.
    ; The conditions nest, so each edge implies every shallower one.
    LDH A, [hIO_TM]
    INC A
    LDH [hIO_TM], A
    LD B, A
    AND $07
    JR NZ, .dispatch
    LD C, $1
    LD A, B
    AND $1F
    JR NZ, .latch
    LD C, $3
    LD A, B
    AND $7F
    JR NZ, .latch
    LD C, $7
    LD A, B
    OR A
    JR NZ, .latch
    LD C, $F
.latch:
    LDH A, [hIO_IT]
    OR C
    LDH [hIO_IT], A
.dispatch:
    ; NB: Only enter interrupt if EIT & IT != 0
    LDH A, [hIO_EIT]
    LD B, A
    LDH A, [hIO_IT]
    AND B
    JR Z, .done
    ; NB: Check I flag is set
    LDH A, [hF]
    BIT 3, A
    JR Z, .done
    RES 3, A
    LDH [hF], A
    LDH A, [hBank]
    PUSH AF
    FAR_CALL rom_0_1_02
    POP AF
    LDH [hBank], A
    LD [$2000], A
    ; NB: Signal an interrupt actually occurred
    LD A, $1
    LDH [hHALT], A
.done:
    POP HL
    POP DE
    POP BC
    POP AF
    RETI

; Call a subroutine in another ROM bank.
; @param A  Destination ROM bank
; @param B  Source ROM bank
; @param HL Subroutine address
_far_call::
    PUSH BC
    LDH [hBank], A
    LD [$2000], A
    LD BC, .done
    PUSH BC
    JP HL
.done:
    POP BC
    LD A, B
    LDH [hBank], A
    LD [$2000], A
    RET

; Jump to another ROM bank.
; @param A  Destination ROM bank
; @param HL Destination address
_far_jump::
    LDH [hBank], A
    LD [$2000], A
    JP HL

; Usage: JUMP_TABLE default_addr, offset1, addr1, ..., offsetN, addrN
MACRO JUMP_TABLE
    ASSERT _NARG % 2 == 1
    FOR I, $80
        DEF _FOUND = 0
        FOR J, 2, _NARG, 2
            IF I == \<J>
                DEF _K = J + 1
                JP \<_K>
                DEF _FOUND = 1
                BREAK
            ENDC
        ENDR
        IF _FOUND == 0
            JP \1
        ENDC
    ENDR
    PURGE _K, _FOUND
ENDM

DEF eIT EQU $00
DEF eEIT EQU $10
DEF eTM30 EQU $20
DEF eTM74 EQU $21
DEF eK0 EQU $40
DEF eCTRL_OSC EQU $70
DEF eCTRL_TM EQU $76

; Read a nibble from E0C6200 RAM.
; @param HL Address of index pointer (e.g. X, Y)
; @return A Nibble from RAM
; @clobber BC, HL
_read_ram::
    LD A, [HL+]
    CP $F
    JR Z, .read_io
    ADD HIGH(wRAM)
    LD B, A
    LD A, [HL]
    LD H, B
    LD L, A
    LD A, [HL]
    RET
.read_io:
    LD A, [HL]
    LD B, 0
    LD C, A
    LD HL, .read_io_table
    ADD HL, BC
    ADD HL, BC
    ADD HL, BC
    JP HL
.read_io_table:
    JUMP_TABLE .read_io_stub, \
        eIT, .read_io_it, \
        eEIT, .read_io_eit, \
        eTM30, .read_io_tm30, \
        eTM74, .read_io_tm74, \
        eK0, .read_io_k0, \
        eCTRL_OSC, .read_io_ctrl_osc, \
        eCTRL_TM, .read_io_stub
.read_io_stub:
    XOR A
    RET
.read_io_it:
    LD HL, hIO_IT
    LD A, [HL]
    LD [HL], 0
    RET
.read_io_eit:
    LDH A, [hIO_EIT]
    RET
.read_io_tm30:
    LDH A, [hIO_TM]
    AND $F
    RET
.read_io_tm74:
    LDH A, [hIO_TM]
    SWAP A
    AND $F
    RET
.read_io_k0:
    LD A, $F
    RET
.read_io_ctrl_osc:
    LDH A, [hIO_CTRL_OSC]
    RET


; Write a nibble to E0C6200 RAM.
; @param A  Nibble to write
; @param HL Address of index pointer (e.g. X, Y)
; @clobber A, BC, D, HL
_write_ram::
    LD D, A
    LD A, [HL+]
    CP $F
    JR Z, .write_io
    ADD HIGH(wRAM)
    LD B, A
    LD A, [HL]
    LD H, B
    LD L, A
    LD [HL], D
    RET
.write_io:
    LD A, [HL]
    LD B, 0
    LD C, A
    LD HL, .write_io_table
    ADD HL, BC
    ADD HL, BC
    ADD HL, BC
    LD A, D
    JP HL
.write_io_table:
    JUMP_TABLE .write_io_stub, \
        eIT, .write_io_stub, \
        eEIT, .write_io_eit, \
        eTM30, .write_io_stub, \
        eTM74, .write_io_stub, \
        eCTRL_OSC, .write_io_ctrl_osc, \
        eCTRL_TM, .write_io_ctrl_tm
.write_io_stub:
    RET
.write_io_eit:
    LDH [hIO_EIT], A
    RET
.write_io_ctrl_osc:
    LDH [hIO_CTRL_OSC], A
    RET
.write_io_ctrl_tm:
    BIT 1, A
    JR Z, .done
    XOR A
    LDH [hIO_TM], A
.done:
    RET
