import re


def sanitize_filename(name):
    """Sanitize company name for use in filenames and directory paths."""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = name.replace(' ', '_')
    return name
