def human_format(num: int) -> str:
    if num >= 1000000:
        return f'{round(num / 1000000, 1)}M'
    if num >= 1000:
        return f'{round(num / 1000, 1)}K'
    return str(num)
