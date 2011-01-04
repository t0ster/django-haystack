"""
This module provides smart way of getting attributes
`obj.attr1.attr2` will be processed as `obj.attr10_0_0attr2`
if 0_0_0 is separator

See `BaseResult` docstring for example.
"""
from haystack.constants import DOTATTR_SEPARATOR
from haystack.utils import is_denorm_attr


class ResultAttr(object):
    """
    Proxy class, grabbed from
    http://code.activestate.com/recipes/496741-object-proxying/
    """
    __slots__ = ["_obj", "__weakref__"]

    def __init__(self, name, obj, result):
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "_obj", obj)
        object.__setattr__(self, "_result", result)

    #
    # proxying (special cases)
    #
    def __getattribute__(self, name):
        try:
            return getattr(object.__getattribute__(self, "_obj"), name)
        except AttributeError:
            name = "%s%s%s" % (object.__getattribute__(self, "_name"), DOTATTR_SEPARATOR, name)
            return getattr(object.__getattribute__(self, "_result"), name)

    def __delattr__(self, name):
        delattr(object.__getattribute__(self, "_obj"), name)

    def __setattr__(self, name, value):
        setattr(object.__getattribute__(self, "_obj"), name, value)

    def __nonzero__(self):
        return bool(object.__getattribute__(self, "_obj"))

    def __str__(self):
        return str(object.__getattribute__(self, "_obj"))

    def __repr__(self):
        return repr(object.__getattribute__(self, "_obj"))

    def __call__(self, *args, **kwargs):
        return self

    def __cmp__(self, other):
        _obj = object.__getattribute__(self, "_obj")
        return cmp(_obj, other)

    def __eq__(self, other):
        _obj = object.__getattribute__(self, "_obj")
        return _obj == other

    def __float__(self):
        _obj = object.__getattribute__(self, "_obj")
        return float(_obj)

    def __abs__(self):
        _obj = object.__getattribute__(self, "_obj")
        return abs(_obj)

    #
    # factories
    #
    _special_names = [
        '__abs__', '__add__', '__and__', '__call__', '__cmp__', '__coerce__',
        '__contains__', '__delitem__', '__delslice__', '__div__', '__divmod__',
        '__eq__', '__float__', '__floordiv__', '__ge__', '__getitem__',
        '__getslice__', '__gt__', '__hash__', '__hex__', '__iadd__', '__iand__',
        '__idiv__', '__idivmod__', '__ifloordiv__', '__ilshift__', '__imod__',
        '__imul__', '__int__', '__invert__', '__ior__', '__ipow__', '__irshift__',
        '__isub__', '__iter__', '__itruediv__', '__ixor__', '__le__', '__len__',
        '__long__', '__lshift__', '__lt__', '__mod__', '__mul__', '__ne__',
        '__neg__', '__oct__', '__or__', '__pos__', '__pow__', '__radd__',
        '__rand__', '__rdiv__', '__rdivmod__', '__reduce__', '__reduce_ex__',
        '__repr__', '__reversed__', '__rfloorfiv__', '__rlshift__', '__rmod__',
        '__rmul__', '__ror__', '__rpow__', '__rrshift__', '__rshift__', '__rsub__',
        '__rtruediv__', '__rxor__', '__setitem__', '__setslice__', '__sub__',
        '__truediv__', '__xor__', 'next',
    ]

    @classmethod
    def _create_class_proxy(cls, theclass):
        """creates a proxy for the given class"""

        def make_method(name):
            def method(self, *args, **kw):
                return getattr(object.__getattribute__(self, "_obj"), name)(*args, **kw)
            return method

        namespace = {}
        for name in cls._special_names:
            if hasattr(theclass, name) and not hasattr(cls, name):
                namespace[name] = make_method(name)
        return type("%s(%s)" % (cls.__name__, theclass.__name__), (cls,), namespace)

    def __new__(cls, obj, *args, **kwargs):
        """
        creates an proxy instance referencing `obj`. (obj, *args, **kwargs) are
        passed to this class' __init__, so deriving classes can define an 
        __init__ method of their own.
        note: _class_proxy_cache is unique per deriving class (each deriving
        class must hold its own cache)
        """
        try:
            cache = cls.__dict__["_class_proxy_cache"]
        except KeyError:
            cls._class_proxy_cache = cache = {}
        try:
            theclass = cache[obj.__class__]
        except KeyError:
            cache[obj.__class__] = theclass = cls._create_class_proxy(obj.__class__)
        ins = object.__new__(theclass)
        return ins


class BaseResult(object):
    """
    >>> class Result(BaseResult):
    ...     def __init__(self, *args, **kwargs):
    ...         self.x = 35
    ...         self.a0_0_0b = 40
    ...         self.y = 5
    ...         self.y0_0_0a = 3
    ...         self.y0_0_0b = 'hello'
    ...         self.y0_0_0c0_0_0x = [1, 2, 3]
    ...         super(Result, self, *args, **kwargs)
    >>> r = Result()
    >>> r.x
    35
    >>> r.x + 40  # r.a.b
    75
    >>> r.x == r.a.b
    False
    >>> r.a.b
    40
    >>> r.y
    5
    >>> # r.y__a.__class__
    >>> # <class ....ResultAttr...>
    >>> r.y.a
    3
    >>> r.y.b
    'hello'
    >>> r.y.c  # Is there any way to raise AtrributeError here?
    None
    >>> r.y.d  # doctest:+ELLIPSIS
    Traceback (most recent call last):
    ...
    AttributeError: 'Result' object has no attribute 'y...d'
    >>> r.y.c.x
    [1, 2, 3]
    >>> r.y__a
    3
    >>> r.y__c__x
    [1, 2, 3]
    >>> r.y__c.x
    [1, 2, 3]
    >>> r.y0_0_0c = 1
    >>> r.y__c.x
    [1, 2, 3]
    >>> r.a.b()
    40
    """
    attr_names = set(('__dict__',))

    def __getattribute__(self, name):
        super_method = super(BaseResult, self).__getattribute__
        if name in BaseResult.attr_names:
            return super_method(name)
        try:
            attr = super_method(name)
        except AttributeError:
            name = name.replace('__', DOTATTR_SEPARATOR)
            try:
                attr = super_method(name)
            except AttributeError:
                if not is_denorm_attr(self, name):
                    raise
                try:
                    attr = super_method(name)
                except AttributeError:
                    attr = None
        res = ResultAttr(name, attr, self)
        return res

if __name__ == '__main__':
    import doctest
    doctest.testmod()
