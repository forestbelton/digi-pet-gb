IF !DEF(PROLOGUE)
DEF PROLOGUE EQU 1

MACRO FAR_CALL
    LD A, BANK(\1)
    LD B, BANK(@)
    LD HL, \1
    CALL _far_call
.done:
ENDM

MACRO FAR_JUMP
    ASSERT _NARG == 1 || _NARG == 2
    IF _NARG == 1
        LD A, BANK(\1)
        LD HL, \1
        JP _far_jump
    ELSE
        ASSERT !STRCMP("\1", "Z") || !STRCMP("\1", "NZ") || !STRCMP("\1", "C") || !STRCMP("\1", "NC")
        IF !STRCMP("\1", "Z")
            JR NZ, .done\@
        ELIF !STRCMP("\1", "NZ")
            JR Z, .done\@
        ELIF !STRCMP("\1", "C")
            JR NC, .done\@
        ELIF !STRCMP("\1", "NC")
            JR C, .done\@
        ENDC
        LD A, BANK(\2)
        LD HL, \2
        JP _far_jump
.done\@:
    ENDC
ENDM

SECTION "Header", ROM0[$100]
    JP _start

; NB: Leave space for cartridge header
DS $150 - @, 0

SECTION "Entrypoint", ROM0[$150]
_start:
    FAR_JUMP rom_0_1_00

SECTION "Utilities", ROM0

; Call a subroutine in another ROM bank.
; @param A  Destination ROM bank
; @param B  Source ROM bank
; @param HL Subroutine address
_far_call::
    PUSH BC
    LD [$2000], A
    LD BC, .done
    PUSH BC
    JP HL
.done:
    POP BC
    LD A, B
    LD [$2000], A
    RET

; Jump to another ROM bank.
; @param A  Destination ROM bank
; @param HL Destination address
_far_jump::
    LD [$2000], A
    JP HL

; Read a nibble from E0C6200 RAM.
; @param HL Address of index pointer (e.g. X, Y)
; @return A Nibble from RAM
; @clobber BC, HL
_read_ram::
    LD A, [HL+]
    CP $F
    JR Z, .read_io
    LD B, A
    LD A, [HL+]
    LD C, A
    LD HL, wRAM
    ADD HL, BC
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
    REPT $40
        JP .read_io_stub
    ENDR
    JP .read_io_k0
    REPT $7E
        JP .read_io_stub
    ENDR
.read_io_stub:
    XOR A
    RET
.read_io_k0:
    LD A, $F
    RET


; Write a nibble to E0C6200 RAM.
; @param A  Nibble to write
; @param HL Address of index pointer (e.g. X, Y)
; @clobber A, BC, D, HL
_write_ram::
    LD D, A
    LD A, [HL+]
    LD B, A
    LD A, [HL+]
    LD C, A
    LD HL, wRAM
    ADD HL, BC
    LD [HL], D
    RET

ENDC
