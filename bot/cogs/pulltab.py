import inspect
import os
import random
import traceback
import typing
from collections import Counter

from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.enums.permissions import TacoPermissions
from bot.lib.helpers import MessageHelper
from bot.lib.permissions import Permissions
from bot.lib.settings import Settings
from bot.tacobot import TacoBot
from discord import Interaction, app_commands
from discord.ext import commands


class PullTabCog(TacobotCog):
    group = app_commands.Group(name="pulltab", description="Pulltab commands")

    def __init__(self, bot: TacoBot, settings: Settings, message_helper: MessageHelper, permissions: Permissions):
        super().__init__(bot, "pulltab", settings)
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.message_helper = message_helper
        self.permissions = permissions
        self.ticket_codes = set()
        self.cog_settings = None

    @commands.guild_only()
    @commands.group(name="pulltab", aliases=["pt", "pulltabs"], invoke_without_command=False)
    async def pulltab(self, ctx: typing.Union[commands.Context, Interaction]):
        _method = inspect.stack()[0][3]
        guild_id = 0
        user = None
        if isinstance(ctx, commands.Context):
            guild_id = ctx.guild.id if ctx.guild else 0
            user = ctx.author
        elif isinstance(ctx, Interaction):
            guild_id = ctx.guild.id if ctx.guild else 0
            user = ctx.user

        if user is None:
            return
        cog_settings = self.get_cog_settings(guild_id)
        if not cog_settings:
            self.log.warn(
                guild_id, f"{self._module}.{self._class}.{_method}", "No pulltab settings found for guild"
            )
            return


        if not (
            self.permissions.has_taco_permission(
                guild_id, user, [TacoPermissions.PULLTAB_NO_PURCHASE, TacoPermissions.PULLTAB_NO_REDEEM]
            )
        ):
            # stop processing if the user does not have permission
            # need to prevent the subcommands from being processed
            return
        pass

    @pulltab.command(
        name="purchase",
        description="Purchase a pulltab ticket for a chance to win tacos! Cost: 100 tacos",
        aliases=["buy"],
    )
    @app_commands.default_permissions()
    async def purchase_command(self, ctx: commands.Context, count: int = 1):
        await self._process_pulltab_purchase(ctx, count)

    @group.command(name="purchase", description="Purchase a pulltab ticket for a chance to win tacos! Cost: 100 tacos")
    async def purchase_interaction(self, interaction: Interaction, count: int = 1):
        await self._process_pulltab_purchase(interaction, count)

    @pulltab.command(name="info", description="Get information about pulltab payouts and probabilities")
    async def info_command(self, ctx: commands.Context):
        await self._process_pulltab_info(ctx)

    @group.command(name="info", description="Get information about pulltab payouts and probabilities")
    async def info_interaction(self, interaction: Interaction):
        await self._process_pulltab_info(interaction)

    def _build_payout_message(self, probabilities: typing.List[typing.Dict[str, typing.Any]]) -> str:
        message = "Payouts:\n"
        for p in probabilities:
            rules = p.get("rules", [])
            for rule in rules:
                match = rule["match"]
                reward = rule["reward"]
                multiplier = rule.get("multiplier", 1)
                if multiplier != 1:
                    reward = f"line multiplier x{multiplier}"
                message += f"{match} -> {reward}\n"
        return message

    def _build_probability_message(self, probabilities: typing.List[typing.Dict[str, typing.Any]]) -> str:
        message = "Probabilities:\n"
        total_weight = sum(p['weight'] for p in probabilities)
        for p in probabilities:
            symbol = p['symbol']
            weight = p['weight']
            probability = (weight / total_weight) * 100 if total_weight > 0 else 0
            message += f"{symbol}: {probability:.2f}%\n"
        return message

    async def _process_pulltab_info(self, ctx: typing.Union[commands.Context, Interaction]):
        _method = inspect.stack()[0][3]
        try:
            guild_id = 0
            if self.bot.user is None:
                return
            if isinstance(ctx, commands.Context):
                guild_id = ctx.guild.id if ctx.guild else 0
            elif isinstance(ctx, Interaction):
                guild_id = ctx.guild.id if ctx.guild else 0

            if self.cog_settings is None:
                self.cog_settings = self.get_cog_settings(guild_id)
            cog_settings = self.cog_settings
            if not cog_settings:
                self.log.warn(
                    guild_id, f"{self._module}.{self._class}.{_method}", "No pulltab settings found for guild"
                )
                return
            cost: int = cog_settings.get("cost", 10)
            probabilities: typing.List[typing.Dict[str, typing.Any]] = cog_settings.get("probabilities", [])
            payout_message = self._build_payout_message(probabilities)
            probability_message = self._build_probability_message(probabilities)
            message = f"Cost Per Pulltab: {cost} tacos\n\n{payout_message}\n{probability_message}\n"

            await self._send_message(ctx, message)
        except Exception as e:
            self.log.error(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"Error processing pulltab info: {e}",
                traceback.format_exc(),
            )

    async def _process_pulltab_purchase(self, ctx: typing.Union[commands.Context, Interaction], count: int = 1):
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            if self.bot.user is None:
                return
            count = self._normalize_count(count, 1, 5)

            if isinstance(ctx, commands.Context):
                guild_id = ctx.guild.id if ctx.guild else 0
                user_id = ctx.author.id
            elif isinstance(ctx, Interaction):
                guild_id = ctx.guild.id if ctx.guild else 0
                user_id = ctx.user.id
            else:
                self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", "Invalid context type")
                return

            if user_id == self.bot.user.id:
                return

            cog_settings = self.get_cog_settings(guild_id)
            cost = cog_settings.get("cost", 10)

            tickets_total_cost = cost * count

            tickets = "ticket" if count == 1 else "tickets"
            tacos = "taco" if tickets_total_cost == 1 else "tacos"

            if not self._validate_user_can_purchase(guild_id, user_id, tickets_total_cost):
                await self._send_message(
                    ctx,
                    f"You do not have enough tacos to purchase {count} pulltab {tickets} (cost: {tickets_total_cost} 🌮 {tacos}).",
                )
                return

            probabilities: typing.List[typing.Dict[str, typing.Any]] = cog_settings.get("probabilities", [])

            if len(probabilities) == 0:
                self.log.warn(
                    guild_id, f"{self._module}.{self._class}.{_method}", "No pulltab probabilities configured for guild"
                )
                return

            symbols = [p['symbol'] for p in probabilities]
            weights = [p['weight'] for p in probabilities]
            rows = 5
            cols = 3

            # generate a random code for the pulltab sequence
            # the code should be alphanumeric
            # the code should be 8 - 16 characters long
            # the code should be unique
            # store the code in self.ticket_codes
            tickets_output = []
            for _ in range(count):
                code = ""
                while not code or code in self.ticket_codes:
                    code = ''.join(
                        random.choices(
                            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=random.randint(8, 16)
                        )
                    )

                # the code is unique, store it
                self.ticket_codes.add(code)
                # the code is used to identify the pulltab sequence
                # to redeem the pulltab sequence, the user must provide the code

                ticket = []
                sheet = random.choices(symbols, weights=weights, k=rows * cols)
                for r in range(rows):
                    row = [sheet[r * cols : (r + 1) * cols]]
                    ticket.append(row)

                sheet_display = ""
                for row in ticket:
                    sheet_display += "||" + "  ".join(row[0]) + "||\n"

                is_winner, reward, lines = self._process_ticket(ticket, cog_settings)
                win_lines = "\n".join(lines)
                self.log.debug(
                    guild_id,
                    f"{self._module}.{self._class}.{_method}",
                    f"Ticket results {code}:\nWinner: {is_winner}\nReward: {reward}\nWinning Lines: {win_lines}",
                )
                tickets_output.append(f"ticket: ||`{code}`||\n\n{sheet_display}\n")

            sheets_display = "\n".join(tickets_output)
            redeem_message = "redeem with `/pulltab redeem <code>` or `.taco pulltab redeem <code>`"

            await self._send_message(ctx, f"{sheets_display}\n{redeem_message}")
        except Exception as e:
            await self.message_helper.notify_of_error(ctx)
            self.log.error(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"Error processing pulltab purchase: {e}",
                traceback.format_exc(),
            )

    def _save_ticket(
        self,
        guild_id: int,
        user_id: int,
        code: str,
        ticket: typing.List[typing.List[str]],
        cog_settings: typing.Dict[str, typing.Any],
    ):
        pass

    def _process_ticket(
        self, ticket: typing.List[str], cog_settings: typing.Dict[str, typing.Any]
    ) -> typing.Tuple[bool, int, typing.List[str]]:
        """Process a pulltab ticket.
        Returns a tuple of (is_winner: bool, reward: int, winning_lines: list[str]).
        Matching rules are tested by exact sequence or by token counts (so '🌮🌮' matches if
        there are two tacos anywhere in the row). When multiple rules for the same symbol
        match the row, only the highest reward for that symbol is awarded to avoid
        double-counting (e.g., a triple taco will not also claim a single- and double-
        taco payout).
        """

        probabilities: typing.List[typing.Dict[str, typing.Any]] = cog_settings.get("probabilities", [])

        total_reward = 0
        is_winner = False
        winning_lines = []

        # rules: [
        #     {
        #         match: '🌮',
        #         reward: 100
        #     },
        #     {
        #         // this means any two tacos ont the row
        #         match: '🌮🌮',
        #         reward: 1000
        #     },
        #     {
        #         match: '🌮🌮🌮',
        #         reward: 10000
        #     }
        # ]

        for row in ticket:
            # ticket rows may be stored as [[sym1, sym2, sym3]] or [sym1, sym2, sym3]
            # Normalize to a list of symbol strings
            if len(row) == 1 and isinstance(row[0], list):
                row_symbols = row[0]
            else:
                row_symbols = row
            # configured symbols are those that have probability entries; rows may include other symbols
            configured_symbols = [p['symbol'] for p in probabilities]
            # For this row, collect the best matched rule for each symbol
            row_matches: list[typing.Tuple[str, int, str, int]] = []  # (symbol, reward, match_str, multiplier)
            for p in probabilities:
                rules = p.get('rules', [])
                matched_rules = []
                for rule in rules:
                    match = rule['match']
                    reward = rule['reward']
                    multiplier = rule.get('multiplier', 1)

                    # Build counters for the row and for the match string using the configured symbols
                    match_counts = {s: match.count(s) for s in configured_symbols}
                    row_counts = Counter(row_symbols)

                    # exact match (order and count)
                    exact_match = match == ''.join(row_symbols)

                    # count match: all symbols in match appear in the row at least the same number of times
                    count_match = False
                    # Only consider count-match if the number of match tokens is less than the row length (e.g., any 2-of-3)
                    if sum(match_counts.values()) < len(row_symbols):
                        # match must have at least one configured symbol
                        if any(v > 0 for v in match_counts.values()):
                            count_match = all(
                                row_counts.get(sym, 0) >= count for sym, count in match_counts.items() if count > 0
                            )

                    matched = exact_match or count_match
                    if matched:
                        line_reward = reward * multiplier
                        matched_rules.append((line_reward, match, multiplier))

                if matched_rules:
                    # choose the highest reward for this symbol's rule set (prevents awarding smaller overlapping matches)
                    # matched_rules contains (line_reward, match, multiplier)
                    max_reward, max_match, max_mult = max(matched_rules, key=lambda t: t[0])
                    # record this symbol's winning candidate for the row
                    row_matches.append((p['symbol'], max_reward, max_match, max_mult))

            # Now evaluate all symbol matches for the row
            # If any matched rule has multiplier == 0 then the whole row is a losing line
            if any(mult == 0 for (_sym, _r, _m, mult) in row_matches):
                # row contains a deny rule (e.g., skull) so no payout for this row
                continue

            # Otherwise award all matched rules for the row (one per symbol)
            for _sym, r, m, _mult in row_matches:
                line_message = f"{m} -> {r}"
                # each line is its own winner; allow the same match message to appear multiple times
                total_reward += r
                is_winner = True if r > 0 else is_winner
                winning_lines.append(line_message)

        return is_winner, total_reward, winning_lines

    def _redeem_ticket(self, guild_id: int, user_id: int, code: str) -> typing.Tuple[bool, int, str]:
        """Redeem a pulltab ticket.
        Returns a tuple of (success: bool, reward: int, message: str)
        """
        return False, 0, self.settings.get_string(guild_id, "pulltab_redeem_invalid_code")

    def _validate_user_can_purchase(self, guild_id: int, user_id: int, total_cost: int) -> bool:
        return True

    def _normalize_count(self, count: int, min_value: int, max_value: int) -> int:
        if count < min_value:
            return min_value
        if count > max_value:
            return max_value
        return count

    async def _send_message(self, ctx: typing.Union[commands.Context, Interaction], message: str):
        _method = inspect.stack()[0][3]
        if isinstance(ctx, commands.Context):
            await ctx.send(message)
        elif isinstance(ctx, Interaction):
            await ctx.response.send_message(message)
        else:
            guild_id = ctx.guild.id if ctx.guild else 0
            self.log.error(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"Invalid context type for sending message: cannot send message: {message}",
            )


async def setup(bot: TacoBot):
    settings = Settings()
    message_helper = MessageHelper(bot, settings)
    permissions = Permissions(bot, settings)
    await bot.add_cog(PullTabCog(bot, settings, message_helper, permissions))
