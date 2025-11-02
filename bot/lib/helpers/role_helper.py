import inspect
import os
import traceback
from typing import List

import discord

from bot.lib import logger, settings
from bot.lib.enums import loglevel


class RoleHelper:
    """Helper for bulk add/remove role operations on a member.

    Behavior:
    - If user has any role in check_list OR allow_everyone=True, proceed
    - Remove any roles in remove_list that the user currently has
    - Add any roles in add_list that the user does not have
    - Logs actions and swallows Discord errors (warn level)
    """

    def __init__(self, bot) -> None:
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]
        self.bot = bot
        self.settings = settings.Settings()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()] if self.settings.log_level else None
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG
        self.log = logger.Log(minimumLogLevel=log_level)

    async def add_remove_roles(
        self,
        user: discord.Member,
        check_list: List[str],
        add_list: List[str],
        remove_list: List[str],
        allow_everyone: bool = False,
    ) -> None:
        _method = inspect.stack()[0][3]
        if user is None or user.guild is None:
            self.log.warn(0, f"{self._module}.{self._class}.{_method}", "User or guild is None")
            return

        guild_id = user.guild.id
        # check if the user has any of the watch roles
        user_is_in_watch_role = user.roles and any([str(r.id) for r in user.roles if str(r.id) in check_list])

        if user_is_in_watch_role or allow_everyone:
            # remove the roles from the user
            if remove_list:
                role_list = []
                for role_id in remove_list:
                    role = user.guild.get_role(int(role_id))
                    if role and role in user.roles:
                        role_list.append(role)
                        self.log.info(
                            guild_id,
                            f"{self._module}.{self._class}.{_method}",
                            f"Removed role {role.name} from user {user.display_name}",
                        )

                if role_list and len(role_list) > 0:
                    try:
                        await user.remove_roles(*role_list)
                    except Exception as e:  # noqa: BLE001 - propagate as warn only here
                        self.log.warn(
                            guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc()
                        )
            # add the existing roles back to the user
            if add_list:
                role_list = []
                for role_id in add_list:
                    role = user.guild.get_role(int(role_id))
                    if role and role not in user.roles:
                        role_list.append(role)
                        self.log.info(
                            guild_id,
                            f"{self._module}.{self._class}.{_method}",
                            f"Added role {role.name} to user {user.display_name}",
                        )

                if role_list and len(role_list) > 0:
                    try:
                        await user.add_roles(*role_list)
                    except Exception as e:  # noqa: BLE001 - propagate as warn only here
                        self.log.warn(
                            guild_id, f"{self._module}.{self._class}.{_method}", str(e), traceback.format_exc()
                        )
