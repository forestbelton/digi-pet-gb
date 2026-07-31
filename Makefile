SOURCE_ROM ?= DigimonV1JA.bin

TARGET_MAP := $(SOURCE_ROM:%.bin=%.map)
TARGET_ROM := $(SOURCE_ROM:%.bin=%.gbc)
TARGET_SYM := $(SOURCE_ROM:%.bin=%.sym)

ROM_NAME := $(SOURCE_ROM:%.bin=%)
ROM_TITLE := $(shell echo '$(ROM_NAME)' | tr '[:lower:]' '[:upper:]')

PYFILES := $(shell find recompile -type f -name '*.py')

ASMFILES := $(shell find asm -type f -name "*.asm" -not -name "rom.asm") asm/rom.asm
OFILES := $(ASMFILES:%.asm=%.o)

$(TARGET_ROM) $(TARGET_MAP) $(TARGET_SYM): $(OFILES)
	rgblink \
		--map $(TARGET_MAP) \
		--output $(TARGET_ROM) \
		--sym $(TARGET_SYM) \
		$^
	rgbfix \
		--validate \
		--color-only \
		--mbc-type MBC5 \
		--pad-value 0xFF \
		--title "$(ROM_TITLE)" \
		$@

asm/rom.asm: $(SOURCE_ROM) $(PYFILES)
	python -m recompile -o $@ $<

%.o: %.asm asm/macro.inc asm/hardware.inc
	rgbasm -DUSE_CGB=1 -I asm -o $@ $<

.PHONY: clean

clean:
	rm -f asm/rom.asm asm/*.o *.gb *.gbc *.sym *.map
