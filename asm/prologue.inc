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

SECTION "Entry point", ROM0[$100]
_entry:
    jp _start

SECTION "Program start", ROM0[$150]
_start:
    FAR_JUMP rom_0_1_00

SECTION "Utilities", ROM0

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

_far_jump::
    LD [$2000], A
    JP HL

ENDC
