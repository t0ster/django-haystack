# "Hey, Django! Look at me, I'm an app! For Serious!"
import logging
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.encoding import force_unicode
from django.utils.text import capfirst

from haystack.utils.dotattributes import BaseResult
from haystack.sites import NotRegistered
from haystack.utils import is_denorm_attr


# Not a Django model, but tightly tied to them and there doesn't seem to be a
# better spot in the tree.
class SearchResult(BaseResult):
    """
    A single search result. The actual object is loaded lazily by accessing
    object; until then this object only stores the model, pk, and score.
    
    Note that iterating over SearchResults and getting the object for each
    result will do O(N) database queries, which may not fit your needs for
    performance.
    """
    def __init__(self, app_label, model_name, pk, score, **kwargs):
        self.app_label, self.model_name = app_label, model_name
        self.pk = pk
        self.score = score
        self._object = None
        self._model = None
        self._verbose_name = None
        self._additional_fields = []
        self.stored_fields = None
        self.log = logging.getLogger('haystack')
        self._index_class = None
        
        for key, value in kwargs.items():
            if not key in self.__dict__:
                self.__dict__[key] = value
                self._additional_fields.append(key)
    
    def __repr__(self):
        return "<SearchResult: %s.%s (pk=%r)>" % (self.app_label, self.model_name, self.pk)
    
    def __unicode__(self):
        return force_unicode(self.__repr__())
    
    def __getattribute__(self, name):
        # Process special attributes and methods
        if name in set(
            ['__dict__', '_additional_fields'] + SearchResult.__dict__.keys()):
            return object.__getattribute__(self, name)

        # Process attributes that are not search backend fields
        if (name in self.__dict__ and
            name not in self._additional_fields and
            not is_denorm_attr(self, name)
            ):
            try:
                return object.__getattribute__(self, name)
            except AttributeError:
                return self.process_attr_error(name)

        # Process dot attributes (attr1.attr2)
        try:
            # Because of we are subclass of BaseResult we can do
            # res.some.attr.another.attr
            return super(SearchResult, self).__getattribute__(name)
        except AttributeError:
            return self.process_attr_error(name)

    def process_attr_error(self, name):
        if not self._index_class:
            from haystack import site
            # We need this try/except to pass
            # core.tests.models:SearchResultTestCase.test_init and
            # core.tests.models:SearchResultTestCase.test_missing_object
            try:
                self._index_class = type(site.get_index(self.model))
            except NotRegistered:
                return None

        # We could use methods defined in SearchIndex
        attr = self._index_class.__dict__.get(name, None)
        if callable(attr):
            return lambda *args, **kwargs: attr(self, *args, **kwargs)
        return attr
    
    def _get_object(self):
        if self._object is None:
            if self.model is None:
                self.log.error("Model could not be found for SearchResult '%s'." % self)
                return None
            
            try:
                self._object = self.model._default_manager.get(pk=self.pk)
            except ObjectDoesNotExist:
                self.log.error("Object could not be found in database for SearchResult '%s'." % self)
                self._object = None
        
        return self._object
    
    def _set_object(self, obj):
        self._object = obj
    
    object = property(_get_object, _set_object)
    
    def _get_model(self):
        if self._model is None:
            self._model = models.get_model(self.app_label, self.model_name)
        
        return self._model
    
    def _set_model(self, obj):
        self._model = obj
    
    model = property(_get_model, _set_model)
    
    def _get_verbose_name(self):
        if self.model is None:
            self.log.error("Model could not be found for SearchResult '%s'." % self)
            return u''
        
        return force_unicode(capfirst(self.model._meta.verbose_name))
    
    verbose_name = property(_get_verbose_name)
    
    def _get_verbose_name_plural(self):
        if self.model is None:
            self.log.error("Model could not be found for SearchResult '%s'." % self)
            return u''
        
        return force_unicode(capfirst(self.model._meta.verbose_name_plural))
    
    verbose_name_plural = property(_get_verbose_name_plural)
    
    def content_type(self):
        """Returns the content type for the result's model instance."""
        if self.model is None:
            self.log.error("Model could not be found for SearchResult '%s'." % self)
            return u''
        
        return unicode(self.model._meta)
    
    def get_additional_fields(self):
        """
        Returns a dictionary of all of the fields from the raw result.
        
        Useful for serializing results. Only returns what was seen from the
        search engine, so it may have extra fields Haystack's indexes aren't
        aware of.
        """
        additional_fields = {}
        
        for fieldname in self._additional_fields:
            additional_fields[fieldname] = getattr(self, fieldname)
        
        return additional_fields
    
    def get_stored_fields(self):
        """
        Returns a dictionary of all of the stored fields from the SearchIndex.
        
        Useful for serializing results. Only returns the fields Haystack's
        indexes are aware of as being 'stored'.
        """
        if self._stored_fields is None:
            from haystack import site
            from haystack.exceptions import NotRegistered
            
            try:
                index = site.get_index(self.model)
            except NotRegistered:
                # Not found? Return nothing.
                return {}
            
            self._stored_fields = {}
            
            # Iterate through the index's fields, pulling out the fields that
            # are stored.
            for fieldname, field in index.fields.items():
                if field.stored is True:
                    self._stored_fields[fieldname] = getattr(self, fieldname, u'')
        
        return self._stored_fields
