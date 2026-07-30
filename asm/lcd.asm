INCLUDE "hardware.inc"

; NB: The screen is 32x16 dots, which is drawn as four 8x16 OBJs centered in the
; middle of the screen. OAM is initialized and then never touched again, since
; only the OBJ tile data changes. This leaves the background layer free for
; later.
DEF LCD_OBJ_Y EQU 80
DEF LCD_OBJ_X EQU 72
DEF LCD_TILES EQU $8000
DEF LCD_OAM EQU $FE00

; NB: E0C VRAM is mirrored into wRAM a nibble per byte, part 1 at $CE00 and part
; 2 at $CE80. Screen rows 0-3 read part 2 at column offset o, rows 4-7 part 2 at
; o-1, rows 8-11 part 1 at o, rows 12-15 part 1 at o-1; within a nibble the four
; rows run from bit 3 down to bit 0. Every address is therefore
; $CE00 + ((base + o) & $FF), which _lcd_addrs holds per (row, column).
DEF LCD_VRAM_PAGE EQU $CE

SECTION "LCD state", WRAM0

; NB: One byte per (OBJ, row), holding eight dots. Kept adjacent to the shadow so
; init can clear both in one pass.
wLcdFrame: DS 64
wLcdShadow: DS 160

SECTION "LCD flags", HRAM

hLcdReady: DS 1
hLcdBusy: DS 1

SECTION "LCD", ROM0

_lcd_vblank::
    PUSH AF
    PUSH BC
    PUSH DE
    PUSH HL
    LDH A, [hLcdReady]
    OR A
    JR Z, .done
    XOR A
    LDH [hLcdReady], A
    CALL _lcd_blit
.done:
    POP HL
    POP DE
    POP BC
    POP AF
    RETI

_lcd_stat::
    PUSH AF
    PUSH BC
    PUSH DE
    PUSH HL
    ; NB: The build outlives a frame if the timer preempts it often enough, so
    ; refuse to start a second one on the next LYC match.
    LDH A, [hLcdBusy]
    OR A
    JR NZ, .done
    LD A, 1
    LDH [hLcdBusy], A
    ; NB: Interrupts back on. A full build is longer than one 256 Hz timer
    ; period and IF cannot queue a second tick, so a pass that locked out the
    ; timer would drop one and desync TM. Only WRAM is written here, so the
    ; worst a preempting guest write can do is tear a frame.
    EI
    CALL _lcd_sync
    JR Z, .idle
    CALL _lcd_build
    LD A, 1
    LDH [hLcdReady], A
.idle:
    XOR A
    LDH [hLcdBusy], A
.done:
    POP HL
    POP DE
    POP BC
    POP AF
    RETI

; Copy the prepared frame into OBJ tile data.
; NB: Only the low bitplane is written; the high plane was zeroed at init and
; never changes, so every lit dot is colour 1.
_lcd_blit:
    LD HL, wLcdFrame
    LD DE, LCD_TILES
    LD B, 64
.loop:
    LD A, [HL+]
    LD [DE], A
    INC DE
    INC DE
    DEC B
    JR NZ, .loop
    RET

; Refresh the VRAM shadow.
; @return Z set when nothing changed
_lcd_sync:
    LD C, 0
    LD HL, wLcdShadow
    LD DE, $CE00
    LD B, 80
    CALL .range
    LD DE, $CE80
    LD B, 80
    CALL .range
    LD A, C
    OR A
    RET
.range:
    LD A, [DE]
    INC DE
    CP [HL]
    JR Z, .same
    LD [HL], A
    LD C, 1
.same:
    INC HL
    DEC B
    JR NZ, .range
    RET

; Pack eight dots into D, most significant bit leftmost.
; @param BC Cursor into _lcd_addrs
; @param H  LCD_VRAM_PAGE
FOR N, 4
_lcd_byte{N}:
    REPT 8
        LD A, [BC]
        INC BC
        LD L, A
        LD A, [HL]
        ; NB: Rotate the wanted bit into carry: row R reads bit 3 - (R & 3).
        REPT 4 - N
            RRA
        ENDR
        RL D
    ENDR
    RET
ENDR

_lcd_build:
    LD BC, _lcd_addrs
    LD H, LCD_VRAM_PAGE
    FOR R, 16
        DEF _BIT = R & 3
        FOR K, 4
            CALL _lcd_byte{_BIT}
            LD A, D
            LD [wLcdFrame + 16 * K + R], A
        ENDR
        PURGE _BIT
    ENDR
    RET

_init_lcd::
.waitVBlank:
    LDH A, [rLY]
    CP 144
    JR C, .waitVBlank
    XOR A
    LDH [rLCDC], A

    LD HL, LCD_TILES
    LD BC, 128
.clearTiles:
    XOR A
    LD [HL+], A
    DEC BC
    LD A, B
    OR C
    JR NZ, .clearTiles

    LD HL, LCD_OAM
    LD B, 160
.clearOam:
    XOR A
    LD [HL+], A
    DEC B
    JR NZ, .clearOam

    LD HL, LCD_OAM
    FOR K, 4
        LD A, LCD_OBJ_Y
        LD [HL+], A
        LD A, LCD_OBJ_X + 8 * K
        LD [HL+], A
        LD A, 2 * K
        LD [HL+], A
        XOR A
        LD [HL+], A
    ENDR

    LD HL, wLcdFrame
    LD BC, 64 + 160
.clearBufs:
    XOR A
    LD [HL+], A
    DEC BC
    LD A, B
    OR C
    JR NZ, .clearBufs

    XOR A
    LDH [hLcdReady], A
    LDH [hLcdBusy], A
    LDH [rSCX], A
    LDH [rSCY], A
    LDH [rLYC], A

    ; NB: Colour 1 black; colours 2 and 3 are unused.
    LD A, %00001100
    LDH [rOBP0], A
    LD A, STAT_LYC
    LDH [rSTAT], A
    LD A, LCDC_ON | LCDC_OBJ_16 | LCDC_OBJS
    LDH [rLCDC], A
    RET

SECTION "LCD tables", ROM0

_lcd_addrs:
    FOR R, 16
        IF R < 8
            DEF _BASE = ($80 - ((R >> 2) & 1)) & $FF
        ELSE
            DEF _BASE = ($00 - ((R >> 2) & 1)) & $FF
        ENDC
        FOR COL, 32
            IF COL < 8
                DEF _O = 41 + 2 * COL
            ELIF COL < 16
                DEF _O = 59 + 2 * (COL - 8)
            ELIF COL < 24
                DEF _O = 39 - 2 * (COL - 16)
            ELSE
                DEF _O = 17 - 2 * (COL - 24)
            ENDC
            DB (_BASE + _O) & $FF
            PURGE _O
        ENDR
        PURGE _BASE
    ENDR
