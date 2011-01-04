import re
from django.utils.html import strip_tags
try:
    set
except NameError:
    from sets import Set as set

from haystack.constants import DOTATTR_SEPARATOR


IDENTIFIER_REGEX = re.compile('^[\w\d_]+\.[\w\d_]+\.\d+$')


def get_identifier(obj_or_string):
    """
    Get an unique identifier for the object or a string representing the
    object.
    
    If not overridden, uses <app_label>.<object_name>.<pk>.
    """
    if isinstance(obj_or_string, basestring):
        if not IDENTIFIER_REGEX.match(obj_or_string):
            raise AttributeError("Provided string '%s' is not a valid identifier." % obj_or_string)
        
        return obj_or_string
    
    return u"%s.%s.%s" % (obj_or_string._meta.app_label, obj_or_string._meta.module_name, obj_or_string._get_pk_val())


def check_attr(obj, attr_name, separator='__'):
    """
    *Example*:

    if `obj` has 'one__two__three' attribute and
    `attr_name` is 'one' this will return 'one',
    if `attr_name` is 'one__two__three__four' will return
    'one__two__three'

    >>> class C(object): pass
    >>> c = C()
    >>> c.some__super = 1
    >>> c.some__super__duper = 2
    >>> c.some = C()
    >>> c.some.shit = 3
    >>> c.tag__tag = C()
    >>> c.tag__tag.url = 'url'
    >>> check_attr(c, 'some__super__bla')
    'some__super'
    >>> check_attr(c, 'some__super__duper')
    'some__super__duper'
    >>> check_attr(c, 'some__super123__bla')
    'some'
    >>> check_attr(c, 'some__shit')
    'some'
    >>> check_attr(c, 'some')
    'some'
    >>> check_attr(c, 'wtf')
    >>> check_attr(c, 'wtf__shit')
    >>> check_attr(c, 'tag__tag__url')
    'tag__tag'
    >>> c.a0_0_0b = 1
    >>> check_attr(c, 'a0_0_0b0_0_0c', '0_0_0')
    'a0_0_0b'
    """
    def proccess(attr1, attr2):
        attr = separator.join([attr1, attr2])
        if hasattr(obj, attr):
            return attr
        return attr1

    if hasattr(obj, attr_name):
        return attr_name
    splited_attr = attr_name.split(separator)
    attr = reduce(proccess, splited_attr)
    if not hasattr(obj, attr):
        return None
    return attr


def check_attr_in_dict(obj, attr_name, separator='__'):
    """
    >>> class C(object): pass
    >>> c = C()
    >>> c.a0_0_0b = 1
    >>> check_attr_in_dict(c, 'a0_0_0b0_0_0c', '0_0_0')
    'a0_0_0b'
    """
    def proccess(attr1, attr2):
        attr = separator.join([attr1, attr2])
        if attr in obj.__dict__:
            return attr
        return attr1

    if attr_name in obj.__dict__:
        return attr_name
    splited_attr = attr_name.split(separator)
    attr = reduce(proccess, splited_attr)
    if not attr in obj.__dict__:
        return None
    return attr


def is_denorm_attr(obj, name):
    return bool([attr for attr in obj.__dict__ if \
                     "%s%s" % (name, DOTATTR_SEPARATOR) in attr])


class Highlighter(object):
    css_class = 'highlighted'
    html_tag = 'span'
    max_length = 200
    text_block = ''
    
    def __init__(self, query, **kwargs):
        self.query = query
        
        if 'max_length' in kwargs:
            self.max_length = int(kwargs['max_length'])
        
        if 'html_tag' in kwargs:
            self.html_tag = kwargs['html_tag']
        
        if 'css_class' in kwargs:
            self.css_class = kwargs['css_class']
        
        self.query_words = set([word.lower() for word in self.query.split() if not word.startswith('-')])
    
    def highlight(self, text_block):
        self.text_block = strip_tags(text_block)
        highlight_locations = self.find_highlightable_words()
        start_offset, end_offset = self.find_window(highlight_locations)
        return self.render_html(highlight_locations, start_offset, end_offset)
    
    def find_highlightable_words(self):
        # Use a set so we only do this once per unique word.
        word_positions = {}
        
        # Pre-compute the length.
        end_offset = len(self.text_block)
        lower_text_block = self.text_block.lower()
        
        for word in self.query_words:
            if not word in word_positions:
                word_positions[word] = []
            
            start_offset = 0
            
            while start_offset < end_offset:
                next_offset = lower_text_block.find(word, start_offset, end_offset)
                
                # If we get a -1 out of find, it wasn't found. Bomb out and
                # start the next word.
                if next_offset == -1:
                    break
                
                word_positions[word].append(next_offset)
                start_offset = next_offset + len(word)
        
        return word_positions
    
    def find_window(self, highlight_locations):
        best_start = 0
        best_end = self.max_length
        
        # First, make sure we have words.
        if not len(highlight_locations):
            return (best_start, best_end)
        
        words_found = []
        
        # Next, make sure we found any words at all.
        for word, offset_list in highlight_locations.items():
            if len(offset_list):
                # Add all of the locations to the list.
                words_found.extend(offset_list)
        
        if not len(words_found):
            return (best_start, best_end)
        
        if len(words_found) == 1:
            return (words_found[0], words_found[0] + self.max_length)
        
        # Sort the list so it's in ascending order.
        words_found = sorted(words_found)
        
        # We now have a denormalized list of all positions were a word was
        # found. We'll iterate through and find the densest window we can by
        # counting the number of found offsets (-1 to fit in the window).
        highest_density = 0
        
        for count, start in enumerate(words_found[:-1]):
            current_density = 1
            
            for end in words_found[count + 1:]:
                if end - start < self.max_length:
                    current_density += 1
                else:
                    current_density = 0
                
                # Only replace if we have a bigger (not equal density) so we
                # give deference to windows earlier in the document.
                if current_density > highest_density:
                    best_start = start
                    best_end = start + self.max_length
                    highest_density = current_density
        
        return (best_start, best_end)
    
    def render_html(self, highlight_locations=None, start_offset=None, end_offset=None):
        # Start by chopping the block down to the proper window.
        highlighted_chunk = self.text_block[start_offset:end_offset]
        
        for word in self.query_words:
            word_re = re.compile("(%s)" % word, re.I)
            
            if self.css_class:
                highlighted_chunk = re.sub(word_re, r'<%s class="%s">\1</%s>' % (self.html_tag, self.css_class, self.html_tag), highlighted_chunk)
            else:
                highlighted_chunk = re.sub(word_re, r'<%s>\1</%s>' % (self.html_tag, self.html_tag), highlighted_chunk)
        
        if start_offset > 0:
            highlighted_chunk = '...%s' % highlighted_chunk
        
        if end_offset < len(self.text_block):
            highlighted_chunk = '%s...' % highlighted_chunk
        
        return highlighted_chunk
