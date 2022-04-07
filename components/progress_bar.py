class ProgressBarMessage:
    def __init__(
        self, client, channel, content, steps=20, empty_char='·', full_char='█', last_full_char=None
    ):
        # Discord attributes
        self._client = client
        self._channel = channel
        self._message = None

        self._content = content
        self._last_content = None
        self._steps = steps
        self._empty_char = empty_char
        self._full_char = full_char
        self._last_full_char = last_full_char

    async def delete(self):
        """Delete the discord message."""
        if not self._message:
            return
        await self._message.delete()

    async def send(self, comment=None):
        """Create the discord message."""
        await self.update(0, 1, comment=comment)

    async def update(self, complete, total, comment=None):
        """Update the progress bar."""
        assert complete <= total

        # Generate content
        percentage = 100 * complete / total
        content = self._generate_content(percentage, comment=comment)

        if content == self._last_content:
            # Don't update the message if the content didn't change
            return

        # Edit message
        self._last_content = content
        await self._edit_message(content)

    def _generate_content(self, percentage, comment=None):
        content = self._content.format(
            progress_bar=self._generate_progress_bar_string(percentage),
            percentage=percentage,
            comment=comment or '',
        )
        return content

    def _generate_progress_bar_string(self, percentage):
        """Generate the progress bar string."""
        steps_complete = int(percentage // (100 / self._steps))
        steps_incomplete = self._steps - steps_complete

        steps = []
        if steps_complete:
            steps.extend([self._full_char] * (steps_complete - 1))
            steps.append(self._last_full_char or self._full_char)
        steps.extend([self._empty_char] * steps_incomplete)

        return ''.join(steps)

    async def _edit_message(self, content):
        """Edit the discord message with the new content.

        Creates the discord message if it doesn't exist yet.
        """
        if self._message:
            await self._message.edit(content=content)
        else:
            self._message = await self._channel.send(content)
