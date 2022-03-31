import logging.config

from utils import env

# Logging
LOG_LEVEL = env.get('LOG_LEVEL', 'INFO')

# Discord
DISCORD_TOKEN = env.require('DISCORD_TOKEN')
DISCORD_SERVER_ID = int(env.require('DISCORD_SERVER_ID'))
DISCORD_SQUAD_CHANNEL_ID = int(env.require('DISCORD_SQUAD_CHANNEL_ID'))

# BattleMetrics
BM_TOKEN = env.require('BM_TOKEN')
BM_PLAYERS = {
    281939989: 'abe',
    # 0: 'Boouya',
    184191499: 'Buck',
    151189529: 'Davil',
    # 0: 'Drk',
    # 0: 'Eddan',
    # 0: 'Emmo',
    72834906: 'Gunter',
    267265760: 'Hunter',
    # 0: 'in7sec',
    107913625: 'Jks',
    310278335: 'Jumping',
    549196030: 'Kasper',
    1816255: 'Mulu',
    # 0: 'Petke',
    482010215: 'Stink',
    131050066: 'Tarmo',
    # 0: 'YUmY',
}
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
