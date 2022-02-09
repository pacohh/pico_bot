import logging.config

from utils import env

# Logging
LOG_LEVEL = env.get('LOG_LEVEL', 'INFO')

# Discord
DISCORD_TOKEN = env.require('DISCORD_TOKEN')
DISCORD_SERVER_ID = int(env.require('DISCORD_SERVER_ID'))
DISCORD_PLAYER_LOG_CHANNEL_ID = int(env.require('DISCORD_PLAYER_LOG_CHANNEL_ID'))

# BattleMetrics
BM_TOKEN = env.require('BM_TOKEN')
BM_PLAYER_IDS = [
    281939989,  # abe,
    184191499,  # Buck,
    151189529,  # Davil,
    549196030,  # Kasper,
    1816255,  # Mulu,
    131050066,  # Tarmo,
]
BM_ALLOWED_GAMES = {
    'squad': 'Squad',
    'postscriptum': 'PS',
}


def setup_logging():
    logging.config.dictConfig(
        {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'standard': {'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'},
            },
            'handlers': {
                'console': {
                    'level': LOG_LEVEL,
                    'formatter': 'standard',
                    'class': 'logging.StreamHandler',
                },
            },
            'loggers': {
                '': {
                    'handlers': ['console'],
                    'level': 'DEBUG',
                    'propagate': True,
                },
                'discord': {'level': 'WARNING'},
                'websockets': {'level': 'WARNING'},
                'urllib3': {'level': 'WARNING'},
                'aiocache': {'level': 'WARNING'},
            },
        }
    )
