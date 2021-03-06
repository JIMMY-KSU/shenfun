"""Module for optimized functions

Some methods performed in Python may be slowing down solvers. In this optimization
module we place optimized functions that are to be used instead of default
Python methods. Some methods are implemented solely in Cython and only called
from withing the regular Python modules.

"""
import os
import importlib
from functools import wraps

def optimizer(func):
    """Decorator used to wrap calls to optimized versions of functions."""

    try: # Look for optimized version of function
        mod = os.environ.get('SHENFUN_OPTIMIZATION', 'cython')
        mod = importlib.import_module('shenfun.optimization.'+mod.lower())
        fun = getattr(mod, func.__name__, None)

        @wraps(func)
        def wrapped_function(*args, **kwargs):
            u0 = fun(*args, **kwargs)
            return u0

    except: # Otherwise revert to default numpy implementation
        print(func.__name__ + ' not optimized')
        @wraps(func)
        def wrapped_function(*args, **kwargs):
            u0 = func(*args, **kwargs)
            return u0

    return wrapped_function
