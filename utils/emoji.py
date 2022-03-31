import re

from emoji import UNICODE_EMOJI

CUSTOM_EMOJI_RE = re.compile(r'<:[a-z0-9_]+:(?P<id>\d+)>', flags=re.IGNORECASE)


def is_emoji(string):
    """Check if the given string is an unicode emoji or custom emoji."""
    return is_unicode_emoji(string) or is_custom_emoji(string)


def is_unicode_emoji(string):
    """Check if the given string is an unicode emoji."""
    return string in UNICODE_EMOJI


def is_custom_emoji(string):
    """Check if the given string is a custom emoji."""
    return CUSTOM_EMOJI_RE.match(string) is not None


def build_emoji(emoji_id):
    """
    Helper function to create a `discord.Emoji` instance just from the emoji id
    or a custom emoji string like `<:mordhau:578557889053065217>`.
    """
    # Unicode emojis don't have to be converted to a `discord.Emoji` instance
    if is_unicode_emoji(emoji_id):
        return emoji_id

    if not emoji_id[0] == '<':
        emoji_id = f'<:a:{emoji_id}>'

    return emoji_id
