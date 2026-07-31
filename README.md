# digi-pet-gb

A recompilation project to run the [Digital Monster](https://en.wikipedia.org/wiki/Digital_Monster) virtual pet on the Game Boy Color. 100% human written.

**NOTE**: A ROM dump is required to build the Game Boy ROM. Supported ROMs are listed below:

| Name              | SHA1                                     |
| ----------------- | ---------------------------------------- |
| `DigimonV1JA.bin` | 1dde9b0aa81c8f4a1e22d3a79d4743833fc6cba7 |

## Dependencies

Make sure you have [make](https://www.gnu.org/software/make/manual/make.html), [Python](https://www.python.org/), and [rgbds](https://rgbds.gbdev.io/) installed.

## Build

From the project root:

```
$ make
```

`DigimonV1JA.gbc` should be produced in the same directory. If you'd like to override the source ROM used:

```
$ SOURCE_ROM=<path/to/rom.bin> make
```
