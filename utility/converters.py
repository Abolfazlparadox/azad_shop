# converters.py
import re

class UnicodeSlugConverter:
    # This regex accepts letters, digits, underscores, hyphens, and Persian characters (Unicode Arabic block)
    regex = r'[-\w\u0600-\u06FF]+'

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value
