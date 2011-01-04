# A couple models for Haystack to test with.
import datetime
from django.db import models


class Mock(object):
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class MockTag(models.Model):
    name = models.CharField(max_length=32)


class MockModel(models.Model):
    author = models.CharField(max_length=255)
    foo = models.CharField(max_length=255, blank=True)
    pub_date = models.DateTimeField(default=datetime.datetime.now)
    tag = models.ForeignKey(MockTag, null=True)
    
    def __unicode__(self):
        return self.author
    
    def hello(self):
        return 'World!'

    hello__func = lambda *args, **kwargs: Mock(world='Hello World!')


class AnotherMockModel(models.Model):
    author = models.CharField(max_length=255)
    pub_date = models.DateTimeField(default=datetime.datetime.now)
    
    def __unicode__(self):
        return self.author
