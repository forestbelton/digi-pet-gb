SECTION "WRAM", WRAM0[$C000]

wRAM:: DS $ED0

; NB: The boot ROM leaves SP at $FFFE, which grows the stack down through HRAM
; and into the register mirrors below. The guest's own pushes land here too, so
; give it a bank of its own well clear of them.
SECTION "Stack", WRAMX[$D000]

wStack:: DS $1000

SECTION "HRAM", HRAM[$FF80]

hBank:: DS 1
hHALT:: DS 1

hA:: DS 1
hB:: DS 1
hF:: DS 1

hX::
hXP:: DS 1
hXHL:: DS 1

hY::
hYP:: DS 1
hYHL:: DS 1

hIO_CTRL_OSC:: DS 1
hIO_CTRL_LCD:: DS 1
hIO_CTRL_TM: DS 1
hIO_TM:: DS 1
hIO_IT:: DS 1
hIO_EIT:: DS 1
