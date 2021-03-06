import importlib
import inspect
import functools
import os
import sys
import traceback
from typing import *


_DEBUG = False

def is_iterable(o: object) -> bool:
    try:
        iter(o)
        return True
    except TypeError:
        return False

def set_debug(debug: bool):
    global _DEBUG
    _DEBUG = debug


def debug(*a):
    if not _DEBUG:
        return
    stack = traceback.extract_stack()
    frame = stack[-2]
    indent = len(stack) - 3
    print('|{}|{}() {}'.format(
        ' ' * indent, frame.name, ' '.join(map(str, a))), file=sys.stderr)


class NotFound(ValueError):
    pass

class ErrorDuringImport(Exception):
    pass


def walk_qualname(obj: object, name: str) -> object:
    '''
    >>> walk_qualname(list, 'append') == list.append
    True
    >>> class Foo:
    ...   class Bar:
    ...     def doit():
    ...       pass
    >>> walk_qualname(Foo, 'Bar.doit') == Foo.Bar.doit
    True
    '''
    for part in name.split('.'):
        if part == '<locals>':
            raise ValueError(
                'object defined inline are non-addressable(' + name + ')')
        if not hasattr(obj, part):
            raise NotFound('Name "' + part + '" not found')
        obj = getattr(obj, part)
    return obj


def load_by_qualname(name: str) -> object:
    '''
    >>> type(load_by_qualname('os'))
    <class 'module'>
    >>> type(load_by_qualname('os.path'))
    <class 'module'>
    >>> type(load_by_qualname('os.path.join'))
    <class 'function'>
    >>> type(load_by_qualname('pathlib.Path'))
    <class 'type'>
    >>> type(load_by_qualname('pathlib.Path.is_dir'))
    <class 'function'>
    '''
    parts = name.split('.')
    for i in reversed(range(1, len(parts) + 1)):
        cur_module_name = '.'.join(parts[:i])
        try:
            module = importlib.import_module(cur_module_name)
        except ModuleNotFoundError:
            continue
        except Exception as e:
            raise ErrorDuringImport(e, traceback.extract_tb(sys.exc_info()[2])[-1])
        remaining = '.'.join(parts[i:])
        if remaining:
            return walk_qualname(module, remaining)
        else:
            return module
    return None


def extract_module_from_file(filename: str) -> Tuple[str, str]:
    module_name = inspect.getmodulename(filename)
    dirs = []
    if module_name and module_name != '__init__':
        dirs.append(module_name)
    path = os.path.split(os.path.realpath(filename))[0]
    while os.path.exists(os.path.join(path, '__init__.py')):
        path, cur = os.path.split(path)
        dirs.append(cur)
    dirs.reverse()
    module = '.'.join(dirs)
    return path, module


def memo(f):
    """ Memoization decorator for a function taking a single argument """
    saved = {}
    @functools.wraps(f)
    def memo_wrapper(a):
        if not a in saved:
            saved[a] = f(a)
        return saved[a]
    return memo_wrapper


_T = TypeVar('_T')


class IdentityWrapper(Generic[_T]):
    def __init__(self, o: _T):
        self.o = o

    def __hash__(self):
        return id(self.o)

    def __eq__(self, o):
        return hash(self) == hash(o)

class AttributeHolder:
    def __init__(self, attrs: Mapping[str, object]):
        for (k, v) in attrs.items():
            self.__dict__[k] = v


class CrosshairInternal(Exception):
    def __init__(self, *a):
        Exception.__init__(self, *a)
        debug('CrosshairInternal', str(self))


class UnexploredPath(Exception):
    pass


class UnknownSatisfiability(UnexploredPath):
    pass


class PathTimeout(UnexploredPath):
    pass


class CrosshairUnsupported(UnexploredPath):
    def __init__(self, *a):
        debug('CrosshairUnsupported. Stack trace:\n' +
              ''.join(traceback.format_stack()))


class IgnoreAttempt(Exception):
    def __init__(self, *a):
        debug('IgnoreAttempt', str(self))
