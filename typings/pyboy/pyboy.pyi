from typing import Any, Callable

class _RegisterFile:
    A: int
    B: int
    C: int
    D: int
    E: int
    F: int
    HL: int
    SP: int
    PC: int

class _Memory:
    def __getitem__(self, key: int) -> int: ...

class PyBoy:
    memory: _Memory
    register_file: _RegisterFile
    def __init__(self, gamerom: str, *, window: str = ..., **kwargs: Any) -> None: ...
    def tick(self, count: int = ..., render: bool = ..., sound: bool = ...) -> bool: ...
    def hook_register(
        self, bank: int, addr: int, callback: Callable[[Any], None], context: Any
    ) -> None: ...
    def stop(self, save: bool = ...) -> None: ...
