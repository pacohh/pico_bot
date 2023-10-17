import logging.config

from utils import env

# Logging
LOG_LEVEL = env.get('LOG_LEVEL', 'INFO')

# Discord
DISCORD_TOKEN = env.require('DISCORD_TOKEN')
DISCORD_SERVER_ID = int(env.require('DISCORD_SERVER_ID'))

DISCORD_ADMIN_CHANNEL_ID = int(env.require('DISCORD_ADMIN_CHANNEL_ID'))
DISCORD_SQUAD_CHANNEL_ID = int(env.require('DISCORD_SQUAD_CHANNEL_ID'))
DISCORD_MOVIES_CHANNEL_ID = int(env.require('DISCORD_MOVIES_CHANNEL_ID'))
DISCORD_FINANCE_CHANNEL_ID = int(env.require('DISCORD_FINANCE_CHANNEL_ID'))
DISCORD_F1_CHANNEL_ID = int(env.require('DISCORD_F1_CHANNEL_ID'))

VOICE_CREATOR_CHANNEL_ID = int(env.require('VOICE_CREATOR_CHANNEL_ID'))
VOICE1_CHANNEL_ID = int(env.require('VOICE1_CHANNEL_ID'))

DISCORD_TARMO_USER_ID = 71541808957493248
DISCORD_EMMO2GEE_USER_ID = 327081151468404737

DISCORD_APOC_WEBHOOK_URL = env.require('DISCORD_APOC_WEBHOOK_URL')
DISCORD_NEWS_MINIMALIST_WEBHOOK_URL = env.require('DISCORD_NEWS_MINIMALIST_WEBHOOK_URL')
DISCORD_LIVEUAMAP_ISRAEL_PALESTINE_URL = env.require('DISCORD_LIVEUAMAP_ISRAEL_PALESTINE_URL')
DISCORD_HACKERNEWS_WEBHOOK_URL = env.require('DISCORD_HACKERNEWS_WEBHOOK_URL')

# BattleMetrics
BM_TOKEN = env.require('BM_TOKEN')
BM_PLAYERS = {
    '281939989': 'abe',
    '142055479': 'Boouya',
    '184191499': 'Buck',
    '151189529': 'Davil',
    '495011661': 'Drk',
    '3554401': 'Eddan',
    '201740336': 'Emmo',
    '72834906': 'Gunter',
    '734662225': 'Harvey',
    '267265760': 'Hunter',
    '77509268': 'in7sec',
    '107913625': 'Jks',
    '310278335': 'Jumping',
    '549196030': 'Kasper',
    '1816255': 'Mulu',
    '538282779': 'Petke',
    '482010215': 'Stink',
    '131050066': 'Tarmo',
    '401543470': 'Yumy',
}
BM_ALLOWED_GAMES = {
    'squad': 'Squad',
}
BM_SERVER_EMOTES = {
    '2272069': '<:bb:959392964243771413>',  # Blood Bound
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
                'httpx': {'level': 'WARNING'},
            },
        }
    )
