from __future__ import annotations

import logging
import time

from background_tasks.base import CrontabDiscordTask
from commands import ChatCommand

CONVERSATION_MAX_AGE_SECONDS = 24 * 3600  # 24 hours

logger = logging.getLogger(__name__)


class DeleteChatConversations(CrontabDiscordTask):
    """
    Task that checks for old OpenAI chat conversations and deletes them.
    """

    crontab = '* * * * * */30'
    run_on_start = True

    def __init__(self, client):
        super().__init__(client)

    async def work(self):
        # Find old conversations
        to_delete = []
        now = time.time()
        for conversation in ChatCommand.conversations:
            age = now - conversation._start_time
            if age > CONVERSATION_MAX_AGE_SECONDS:
                to_delete.append(conversation)

        # Delete the old conversations
        for conversation in to_delete:
            ChatCommand.conversations.remove(conversation)

        if to_delete:
            logger.info('Deleted %d old chat conversations', len(to_delete))
