SOURCE_ROM ?= DigimonV1JA.bin

TARGET_ROM := $(SOURCE_ROM:%.bin=%.gb)
ROM_NAME := $(SOURCE_ROM:%.bin=%)
ROM_TITLE := $(shell echo '$(ROM_NAME)' | tr '[:lower:]' '[:upper:]')

PYFILES := $(shell find recompile -type f -name '*.py')

ASMFILES := asm/rom.asm asm/ram.asm
OFILES := $(ASMFILES:%.asm=%.o)

$(TARGET_ROM): $(OFILES)
	rgblink $^ -o $@
	rgbfix -v -p 0xFF -t "$(ROM_TITLE)" $@

asm/rom.asm: $(SOURCE_ROM) $(PYFILES)
	python -m recompile -o $@ $<

%.o: %.asm
	rgbasm -I asm -o $@ $<

.PHONY: clean

clean:
	rm -f asm/rom.asm asm/*.o *.gb
