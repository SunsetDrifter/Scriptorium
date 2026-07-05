"""Mutable configuration holder. cli.main() populates CONFIG once at
startup; every other module imports the dict object and reads it live."""

CONFIG = {}


def configure(config, index_entry_extra):
    CONFIG.clear()
    CONFIG.update(config)
    CONFIG["index_entry_extra"] = index_entry_extra
