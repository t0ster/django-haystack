"""
This module provides smart way of getting attributes
`obj.attr1.attr2` will be processed as `obj.attr10_0_0attr2`
if 0_0_0 is separator

See `BaseResult` docstring for example.
"""
SEPARATOR = '0_0_0'


class Null(object):
    def __repr__(self):
        return "<Null>"

    def __str__(self):
        return ''

    def __nonzero__(self):
        return False


class ResultAttrFactory(type):
    _cache = {}

    @classmethod
    def prepare(cls, base, result):
        dict_ = ResultAttr.__dict__.copy()
        dict_.update({
                '_ResultAttr__base': base,
                '_ResultAttr__result': result})
        return ('ResultAttr', (base,), dict_)

    def __new__(cls, base, result):
        if (base, result) in cls._cache:
            type_ = cls._cache[(base, result)]
        else:
            type_ = super(ResultAttrFactory, cls).__new__(
                cls, *cls.prepare(base, result))
            cls._cache[(base, result)] = type_
        return type_

    def __init__(cls, base, result):
        pass


class ResultAttr:
    """Should be used only with ResultAttrFactory"""
    @staticmethod
    def __new__(cls, arg1, name):
        return cls.__base.__new__(cls, arg1)

    def __init__(self, arg1, name):
        self.__name = name
        super(self.__class__, self).__init__(arg1)

    def get_result_attr(self, name):
        if self.__result.is_denorm_attr(name):
            attr = getattr(self.__result, name, None)
        else:
            attr = getattr(self.__result, name)
        return attr

    def __getattr__(self, name):
        lookup_name = "%s%s%s" % (self.__name, SEPARATOR, name)
        attr = self.get_result_attr(lookup_name)
        if type(attr).__name__ == 'ResultAttr':
            type_ = attr.__base
        elif attr is None:
            type_ = Null
        else:
            type_ = type(attr)
        result_attr = ResultAttrFactory(
            type_, self.__result)(attr, lookup_name)
        return result_attr


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
    >>> type(r.x)
    <type 'int'>
    >>> r.a.b
    40
    >>> r.y
    5
    >>> type(r.y)  # doctest:+ELLIPSIS
    <class '....ResultAttr'>
    >>> r.y.a
    3
    >>> r.y.b
    'hello'
    >>> r.y.c  # Is there any way to raise AtrributeError here?
    <Null>
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
    """
    def is_denorm_attr(self, name):
        return bool([k for k in self.__dict__.keys() if \
                         "%s%s" % (name, SEPARATOR) in k])

    def __getattribute__(self, name):
        super_method = super(BaseResult, self).__getattribute__
        if name in ('__dict__', 'is_denorm_attr'):
            return super_method(name)

        # At first we need to check if this is denormalized attribute
        if self.is_denorm_attr(name):
            try:
                attr = super_method(name)
                attr_type = type(attr)
            except AttributeError:
                attr = None
                attr_type = Null
            return ResultAttrFactory(attr_type, self)(attr, name)

        # If name is 'some__atr' replace it with
        # 'someSEPARATORattr'
        elif name.replace('__', SEPARATOR) in self.__dict__.keys():
            return super_method(name.replace('__', SEPARATOR))

        else:
            return super_method(name)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
