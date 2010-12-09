import re

from django.db.models import Q
from django.utils import tree
from django.utils.encoding import force_unicode

from haystack.utils.dotattributes import SEPARATOR
from haystack.constants import VALID_FILTERS, FILTER_SEPARATOR


ATTR_REPL_REGEX = re.compile(r'__(?!%s)' % '|'.join(VALID_FILTERS))


class SearchNode(tree.Node):
    """
    Manages an individual condition within a query.

    Most often, this will be a lookup to ensure that a certain word or phrase
    appears in the documents being indexed. However, it also supports filtering
    types (such as 'lt', 'gt', 'in' and others) for more complex lookups.

    This object creates a tree, with children being a list of either more
    ``SQ`` objects or the expressions/values themselves.
    """
    AND = 'AND'
    OR = 'OR'
    default = AND

    def __repr__(self):
        return '<SQ: %s %s>' % (
            self.connector,
            self.as_query_string(self._repr_query_fragment_callback))

    def _repr_query_fragment_callback(self, field, filter_type, value):
        return '%s%s%s=%s' % (
            field, FILTER_SEPARATOR, filter_type,
            force_unicode(value).encode('utf8'))

    def as_query_string(self, query_fragment_callback):
        """
        Produces a portion of the search query from the current SQ and its
        children.
        """
        result = []

        for child in self.children:
            if hasattr(child, 'as_query_string'):
                result.append(child.as_query_string(query_fragment_callback))
            else:
                expression, value = child
                field, filter_type = self.split_expression(expression)
                result.append(
                    query_fragment_callback(field, filter_type, value))

        conn = ' %s ' % self.connector
        query_string = conn.join(result)

        # If we have sqs.exclude(somefield=None)
        # TODO: this is solr specific so we need to move this
        # somewhere in solr_backend, and is't too hackish
        if query_string and locals().get('value', True) is None:
            if self.negated:
                query_string = '%s:[* TO *]' % field
            else:
                query_string = 'NOT (%s:[* TO *])' % field

        elif query_string:
            if self.negated:
                query_string = 'NOT (%s)' % query_string
            elif len(self.children) != 1:
                query_string = '(%s)' % query_string

        return query_string

    def split_expression(self, expression):
        """Parses an expression and determines the field and filter type."""
        parts = expression.split(FILTER_SEPARATOR)
        field = parts[0]

        if len(parts) == 1 or parts[-1] not in VALID_FILTERS:
            filter_type = 'exact'
        else:
            filter_type = parts.pop()

        return (field, filter_type)


class SQ(Q, SearchNode):
    """
    Manages an individual condition within a query.

    Most often, this will be a lookup to ensure that a certain word or phrase
    appears in the documents being indexed. However, it also supports filtering
    types (such as 'lt', 'gt', 'in' and others) for more complex lookups.
    """
    def prepare_kwargs(self, kwargs):
        """
        Replaces kwargs['some__attr'] with kwargs['some0_0_0attr'] and

        Arguments:
        - `kwargs`: kwargs dictionary
        """
        new_kwargs = {}
        for key, val in kwargs.items():
            if '__' in key:
                key = re.sub(ATTR_REPL_REGEX, SEPARATOR, key)
            new_kwargs[key] = val
        return new_kwargs

    def __init__(self, *args, **kwargs):
        kwargs = self.prepare_kwargs(kwargs)
        super(SQ, self).__init__(*args, **kwargs)
