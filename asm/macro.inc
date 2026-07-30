IF !DEF(MACRO_INC)
DEF MACRO_INC EQU 1

MACRO FAR_CALL
    LD A, BANK(\1)
    LD B, BANK(@)
    LD HL, \1
    CALL _far_call
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

DEF FLAG_C EQU 0
DEF FLAG_Z EQU 1
DEF FLAG_D EQU 2
DEF FLAG_I EQU 3

ENDC
