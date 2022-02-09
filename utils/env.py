import os


def get(name, default=None):
    value = os.getenv(name, default)
    return value


def require(name):
    value = get(name)
    if value is None:
        raise EnvironmentError(f'Environment variable {name} is required')
    return value
