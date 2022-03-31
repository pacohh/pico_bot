def bold(text):
    return f'**{text}**'


def code_block(text, language=None):
    language = language or ''
    return f'```{language or ""}\n{text or " "}\n```'


def code(text):
    return f'`{text}`'


def quote(text):
    return f'"{text}"'


def mention_role_ids(*role_ids):
    mentions = (f'<@&{role_id}>' for role_id in role_ids)
    return ' '.join(mentions)


def format_duration(seconds):
    t = []
    for dm in (60, 60, 24, 7):
        seconds, m = divmod(seconds, dm)
        t.append(m)
    t.append(seconds)
    return ', '.join(
        '%d %s' % (num, unit)
        for num, unit in zip(t[::-1], 'weeks days hours minutes seconds'.split())
        if num
    )
