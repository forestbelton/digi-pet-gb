INCLUDE "hardware.inc"
INCLUDE "macro.inc"

DEF TMA_INIT = 240
IF DEF(USE_CGB)
    DEF TMA_INIT = 224
ENDC

SECTION "VBlank ISR", ROM0[$40]
    JP _lcd_vblank

SECTION "STAT ISR", ROM0[$48]
    JP _lcd_stat

SECTION "Timer ISR", ROM0[$50]
    JP _handle_timer

SECTION "Joypad ISR", ROM0[$60]
    JP _handle_joypad

SECTION "Header", ROM0[$100]
    JP _start

; NB: Leave space for cartridge header
DS $150 - @, 0

SECTION "Entrypoint", ROM0[$150]
_start:
    DI
    LD SP, wStack + $1000

    IF DEF(USE_CGB)
        XOR A
        LDH [rIE], A
        LD A, $30
        LDH [rJOYP], A
        LD A, $01
        LDH [rKEY1], A
        STOP
    ENDC

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

    ; NB: CTRL_LCD resets to ALOFF and DFK0 to all-ones, not zero. K0 idles high
    ; because the buttons are active low with pull-ups.
    LD A, $8
    LDH [hIO_CTRL_LCD], A
    LD A, $F
    LDH [hIO_K0], A
    LDH [hIO_DFK0], A

    ; Initialize timer
    LD A, TMA_INIT
    LDH [rTMA], A
    LD A, TAC_START | TAC_4KHZ
    LDH [rTAC], A

    CALL _init_lcd

    ; Enable interrupts
    LD A, IE_TIMER | IE_VBLANK | IE_STAT | IE_JOYPAD
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
    CALL _sample_input
    LDH A, [hF]
    BIT FLAG_I, A
    JR Z, .done
    ; NB: K0 outranks the timer, matching the core's interrupt priority. EIK0
    ; already gated whether IK0 could be set, so it needs no second mask here.
    LDH A, [hIO_IK0]
    OR A
    JR NZ, .vectorK0
    ; NB: Only enter interrupt if EIT & IT != 0
    LDH A, [hIO_EIT]
    LD B, A
    LDH A, [hIO_IT]
    AND B
    JR Z, .done
    LD A, BANK(rom_0_1_02)
    LD HL, rom_0_1_02
    JR .vector
.vectorK0:
    LD A, BANK(rom_0_1_06)
    LD HL, rom_0_1_06
.vector:
    CALL _vector_guest
.done:
    POP HL
    POP DE
    POP BC
    POP AF
    RETI

; Enter a guest interrupt handler, preserving the interrupted ROM bank.
; @param A  Handler ROM bank
; @param HL Handler address
; @clobber A, BC, D, HL
_vector_guest:
    LD D, A
    LDH A, [hF]
    RES FLAG_I, A
    LDH [hF], A
    LDH A, [hBank]
    PUSH AF
    LD A, D
    LD B, BANK(@)
    CALL _far_call
    POP AF
    LDH [hBank], A
    LD [$2000], A
    ; NB: Signal an interrupt actually occurred
    LD A, $1
    LDH [hHALT], A
    RET

; NB: The device latches IK0 the instant a key line changes, so sampling only on
; the 256 Hz timer tick lands the interrupt up to 4ms late — late enough that the
; guest has already left its HALT and taken a different path. The GB's own joypad
; interrupt fires on the same high-to-low transition, which is what DFK0 = $F
; selects, so it drives sampling here and the timer tick remains a backstop for
; levels and for release edges.
_handle_joypad::
    PUSH AF
    PUSH BC
    PUSH DE
    PUSH HL
    CALL _sample_input
    ; NB: Sampling drives the select lines, which latches a joypad request of its
    ; own on real hardware — so this ISR retriggers itself the moment it returns,
    ; for as long as a button is held. Drop that request here, after the state is
    ; read but before dispatching, so a press arriving during the guest handler
    ; still gets through.
    LDH A, [rIF]
    AND ~IE_JOYPAD & $FF
    LDH [rIF], A
    LDH A, [hF]
    BIT FLAG_I, A
    JR Z, .done
    LDH A, [hIO_IK0]
    OR A
    JR Z, .done
    LD A, BANK(rom_0_1_06)
    LD HL, rom_0_1_06
    CALL _vector_guest
.done:
    POP HL
    POP DE
    POP BC
    POP AF
    RETI

; Sample the joypad into K0 and latch a K0 interrupt on the selected edge.
; NB: K0 is active low with pull-ups — Top is bit 2, Center bit 1, Bottom bit 0 —
; mapped from Up, A and B. The core raises IK0 when a bit both changes while
; enabled in EIK0 and settles on the level DFK0 selects, which is
; (prev ^ new) & EIK0 & (DFK0 ^ new).
; @clobber A, BC, HL
_sample_input:
    LD A, JOYP_GET_CTRL_PAD
    LDH [rP1], A
    LDH A, [rP1]
    LDH A, [rP1]
    LD C, A
    LD A, JOYP_GET_BUTTONS
    LDH [rP1], A
    LDH A, [rP1]
    LDH A, [rP1]
    LD B, A
    ; NB: Leave both groups selected. The joypad interrupt only fires while a
    ; line is selected, and with both groups live any button pulls one low. The
    ; read is ambiguous that way, which is fine — this ISR re-selects each group
    ; before reading it.
    XOR A
    LDH [rP1], A


    LD A, $F
    BIT B_JOYP_UP, C
    JR NZ, .noTop
    RES 2, A
.noTop:
    BIT B_JOYP_A, B
    JR NZ, .noCenter
    RES 1, A
.noCenter:
    BIT B_JOYP_B, B
    JR NZ, .noBottom
    RES 0, A
.noBottom:
    LD B, A
    LDH A, [hIO_K0]
    LD C, A
    LD A, B
    LDH [hIO_K0], A
    XOR C
    LD C, A
    LDH A, [hIO_EIK0]
    AND C
    LD C, A
    LDH A, [hIO_DFK0]
    XOR B
    AND C
    RET Z
    LD A, $1
    LDH [hIO_IK0], A
    RET

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
DEF eIK0 EQU $04
DEF eEIT EQU $10
DEF eEIK0 EQU $14
DEF eTM30 EQU $20
DEF eTM74 EQU $21
DEF eK0 EQU $40
DEF eDFK0 EQU $41
DEF eCTRL_OSC EQU $70
DEF eCTRL_LCD EQU $71
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
        eIK0, .read_io_ik0, \
        eEIT, .read_io_eit, \
        eEIK0, .read_io_eik0, \
        eTM30, .read_io_tm30, \
        eTM74, .read_io_tm74, \
        eK0, .read_io_k0, \
        eDFK0, .read_io_dfk0, \
        eCTRL_OSC, .read_io_ctrl_osc, \
        eCTRL_LCD, .read_io_ctrl_lcd, \
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
    LDH A, [hIO_K0]
    RET
.read_io_ik0:
    LD HL, hIO_IK0
    LD A, [HL]
    LD [HL], 0
    RET
.read_io_eik0:
    LDH A, [hIO_EIK0]
    RET
.read_io_dfk0:
    LDH A, [hIO_DFK0]
    RET
.read_io_ctrl_osc:
    LDH A, [hIO_CTRL_OSC]
    RET
.read_io_ctrl_lcd:
    LDH A, [hIO_CTRL_LCD]
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
        eEIK0, .write_io_eik0, \
        eDFK0, .write_io_dfk0, \
        eTM30, .write_io_stub, \
        eTM74, .write_io_stub, \
        eCTRL_OSC, .write_io_ctrl_osc, \
        eCTRL_LCD, .write_io_ctrl_lcd, \
        eCTRL_TM, .write_io_ctrl_tm
.write_io_stub:
    RET
.write_io_eit:
    LDH [hIO_EIT], A
    RET
.write_io_eik0:
    LDH [hIO_EIK0], A
    RET
.write_io_dfk0:
    LDH [hIO_DFK0], A
    RET
.write_io_ctrl_osc:
    LDH [hIO_CTRL_OSC], A
    RET
.write_io_ctrl_lcd:
    LDH [hIO_CTRL_LCD], A
    RET
.write_io_ctrl_tm:
    BIT 1, A
    JR Z, .done
    XOR A
    LDH [hIO_TM], A
.done:
    RET
