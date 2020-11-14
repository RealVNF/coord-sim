__all__ = []

# Import all module from a the folder
# From https://stackoverflow.com/questions/16852811/python-how-to-import-from-all-modules-in-dir

import pkgutil
import inspect

for loader, name, is_pkg in pkgutil.walk_packages(__path__):
    module = loader.find_module(name).load_module(name)

    for name, value in inspect.getmembers(module):
        if name.startswith('__'):
            continue

        globals()[name] = value
        __all__.append(name)
