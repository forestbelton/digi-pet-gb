SOURCE_ROM ?= DigimonV1JA.bin

TARGET_ROM := $(SOURCE_ROM:%.bin=%.gb)
TARGET_SYM := $(TARGET_ROM:%.gb=%.sym)

ROM_NAME := $(SOURCE_ROM:%.bin=%)
ROM_TITLE := $(shell echo '$(ROM_NAME)' | tr '[:lower:]' '[:upper:]')

PYFILES := $(shell find recompile -type f -name '*.py')

ASMFILES := asm/rom.asm asm/ram.asm
OFILES := $(ASMFILES:%.asm=%.o)

$(TARGET_ROM) $(TARGET_SYM): $(OFILES)
	rgblink $^ -o $(TARGET_ROM) -n $(TARGET_SYM)
	rgbfix -v -m MBC5 -p 0xFF -t "$(ROM_TITLE)" $@

asm/rom.asm: $(SOURCE_ROM) $(PYFILES)
	python -m recompile -o $@ $<

%.o: %.asm asm/prologue.inc
	rgbasm -I asm -o $@ $<

.PHONY: clean

clean:
	rm -f asm/rom.asm asm/*.o *.gb
