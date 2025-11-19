import asyncio
import inspect
import os
import random
import traceback
import typing
from collections import Counter

import discord
from bot.lib import utils
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.enums.permissions import TacoPermissions
from bot.lib.enums.tacotypes import TacoTypes
from bot.lib.helpers import EntityHelper, IdentityHelper, MessageHelper, TacoHelper
from bot.lib.models.PullTabTicketEntry import PullTabTicketEntry
from bot.lib.mongodb.pulltabs import PullTabTicketsDatabase
from bot.lib.permissions import Permissions
from bot.lib.settings import Settings
from bot.tacobot import TacoBot
from bot.ui.PullTabTIcketRedeemView import PullTabTicketRedeemView
from discord import Interaction, app_commands
from discord.ext import commands


class PullTabCog(TacobotCog):
    group = app_commands.Group(name="pulltab", description="Pulltab commands")

    def __init__(
        self,
        bot: TacoBot,
        settings: Settings,
        message_helper: MessageHelper,
        permissions: Permissions,
        identity_helper: IdentityHelper,
        taco_helper: TacoHelper,
        entity_helper: EntityHelper,
        pulltabs_db: PullTabTicketsDatabase,
    ):
        super().__init__(bot, "pulltab", settings)
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.message_helper = message_helper
        self.identity_helper = identity_helper
        self.entity_helper = entity_helper
        self.taco_helper = taco_helper
        self.permissions = permissions
        self.pulltabs_db = pulltabs_db
        self.ticket_codes_cache = set()
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
            self.log.warn(guild_id, f"{self._module}.{self._class}.{_method}", "No pulltab settings found for guild")
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
        name="purchase", description="Purchase a pulltab ticket for a chance to win tacos!", aliases=["buy", "p", "b"]
    )
    async def purchase_command(self, ctx: commands.Context, *, count: int = 1, multiplier: int = 1):
        await self._process_pulltab_purchase(ctx, count=count, multiplier=multiplier)

    @group.command(name="purchase", description="Purchase a pulltab ticket for a chance to win tacos!")
    async def purchase_interaction(self, interaction: Interaction, *, count: int = 1, multiplier: int = 1):
        await self._process_pulltab_purchase(interaction, count=count, multiplier=multiplier)

    @pulltab.command(name="info", aliases=["i"], description="Get information about pulltab payouts and probabilities")
    async def info_command(self, ctx: commands.Context, *, multiplier: int = 1):
        await self._process_pulltab_info(ctx, multiplier=multiplier)

    @group.command(name="info", description="Get information about pulltab payouts and probabilities")
    async def info_interaction(self, interaction: Interaction, multiplier: int = 1):
        await self._process_pulltab_info(interaction, multiplier=multiplier)

    @pulltab.command(name="redeem", aliases=["r"], description="Redeem pulltab ticket")
    async def redeem_command(self, ctx: commands.Context, *, code: str) -> None:
        await self._process_pulltab_redeem(ctx, code=code)

    @group.command(name="redeem", description="Redeem pulltab ticket")
    async def redeem_interaction(self, interaction: Interaction, *, code: str) -> None:
        await self._process_pulltab_redeem(interaction, code=code)

    def _build_payout_message(self, cog_settings: typing.Dict[str, typing.Any], multiplier: int = 1) -> str:
        probabilities: typing.List[typing.Dict[str, typing.Any]] = cog_settings.get("probabilities", [])
        multiplier_settings = cog_settings.get("multiplier", {})

        base_increase = multiplier_settings.get("base_increase", 0.5)
        max_multiplier = multiplier_settings.get("max", 100)

        multiplier = self._clamp(multiplier, 1, max_multiplier)

        effective_multiplier = self._calculate_multiplier(multiplier, base_increase=base_increase)

        message = f"Payouts (based on multiplier x{multiplier}):\n"
        for p in probabilities:
            rules = p.get("rules", [])
            for rule in rules:
                match = rule["match"]
                reward = int(rule.get("reward", 0))
                rule_multiplier = rule.get("multiplier", 1)
                if rule_multiplier != 1:
                    reward = f"line multiplier x{rule_multiplier}"

                effective_reward = int(reward * effective_multiplier) if isinstance(reward, int) else reward
                message += f"{match} -> {effective_reward}\n"
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

    def _build_cost_multiplier_message(self, cog_settings: typing.Dict[str, typing.Any], multiplier: int = 1) -> str:
        purchase_settings = cog_settings.get("purchase", {})
        base_cost = int(purchase_settings.get("cost", 10))
        cost = base_cost * multiplier
        max_purchase = int(purchase_settings.get("max", 5))
        multiplier_settings = cog_settings.get("multiplier", {})
        base_increase = float(multiplier_settings.get("base_increase", 0.05))
        max_multiplier = int(multiplier_settings.get("max", 100))
        # Build a friendly explanatory message for users
        # Show base cost, how many can be purchased at once, and how multipliers affect cost and reward
        pct = base_increase * 100
        message_lines = []
        message_lines.append(f"Cost per ticket: {cost} tacos (with multiplier x{multiplier})")
        message_lines.append(f"Max tickets per purchase: {max_purchase}")
        message_lines.append(f"Multiplier: {multiplier} (max {max_multiplier})")
        message_lines.append("")
        message_lines.append("How multiplier works:")
        message_lines.append(
            "- Buying with a multiplier increases the TOTAL COST linearly: total_cost = cost * count * multiplier\n"
        )
        message_lines.append(
            f"  (Example: buying 3 tickets with multiplier {multiplier} costs {base_cost} * 3 * {multiplier} = {base_cost * 3 * multiplier} tacos)"
        )
        message_lines.append("")
        message_lines.append(
            f"- The multiplier also increases the EFFECTIVE REWARD you can win. Each multiplier point increases rewards by {pct:.1f}% of base value."
        )
        message_lines.append(
            f"  Effective reward multiplier is calculated as: effective = 1 + (multiplier * {pct:.1f}% / 100).\n"
        )
        # show a couple of clear examples using the configured base_increase
        effective_example = self._calculate_multiplier(multiplier, base_increase=base_increase)
        message_lines.append(
            f"  (Example: with multiplier {multiplier} and base increase {pct:.1f}%, effective = {effective_example:.2f} → a 100-taco line becomes ~{round(100 * effective_example)} tacos)\n"
        )
        example_mul2 = min(10, max(2, int(max_multiplier if max_multiplier < 10 else 10)))
        effective_example2 = self._calculate_multiplier(example_mul2, base_increase=base_increase)
        message_lines.append(f"  (Example: with multiplier {example_mul2}, effective = {effective_example2:.2f})")
        message_lines.append("")
        message_lines.append(f"- Max multiplier allowed: {max_multiplier}")
        message_lines.append("")
        message_lines.append("Notes:")
        message_lines.append("- Multiplier increases COST immediately (you pay more up-front).")
        message_lines.append(
            "- Multiplier increases REWARD potential (line rewards are multiplied by the effective multiplier and rounded)."
        )
        message_lines.append(
            "- If you choose multiplier=1 you pay the base price and receive no extra reward multiplier."
        )
        message_lines.append("")

        return "\n".join(message_lines)

    async def _process_pulltab_info(self, ctx: typing.Union[commands.Context, Interaction], *, multiplier: int = 1):
        _method = inspect.stack()[0][3]
        try:
            if isinstance(ctx, Interaction) and not ctx.response.is_done():
                await ctx.response.defer(ephemeral=True)

            guild_id = 0
            if self.bot.user is None:
                return
            if isinstance(ctx, commands.Context):
                guild_id = ctx.guild.id if ctx.guild else 0
            elif isinstance(ctx, Interaction):
                guild_id = ctx.guild.id if ctx.guild else 0

            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings:
                self.log.warn(
                    guild_id, f"{self._module}.{self._class}.{_method}", "No pulltab settings found for guild"
                )
                return

            probabilities: typing.List[typing.Dict[str, typing.Any]] = cog_settings.get("probabilities", [])
            payout_message = self._build_payout_message(cog_settings, multiplier=multiplier)
            probability_message = self._build_probability_message(probabilities)
            cost_multiplier_message = self._build_cost_multiplier_message(cog_settings, multiplier=multiplier)
            message = f"{cost_multiplier_message}\n" f"{payout_message}\n" f"{probability_message}"

            await self._send_message(ctx, message, ephemeral=True)
        except Exception as e:
            self.log.error(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"Error processing pulltab info: {e}",
                traceback.format_exc(),
            )

    async def _process_pulltab_purchase(
        self, ctx: typing.Union[commands.Context, Interaction], *, count: int = 1, multiplier: int = 1
    ):
        _method = inspect.stack()[0][3]
        guild_id = 0
        try:
            # Defer interaction immediately to avoid 3-second timeout
            if isinstance(ctx, Interaction) and not ctx.response.is_done():
                await ctx.response.defer(ephemeral=True)

            if self.bot.user is None:
                return

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

            user = await self.entity_helper.get_or_fetch_user(user_id)
            if user is None:
                self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", "Could not fetch user")
                return
            user_taco_count = self.taco_helper.get_taco_count(guildId=guild_id, userId=user_id)
            if user_taco_count is None:
                user_taco_count = 0

            cog_settings = self.get_cog_settings(guild_id)
            if not cog_settings:
                self.log.warn(
                    guild_id, f"{self._module}.{self._class}.{_method}", "No pulltab settings found for guild"
                )
                return

            purchase_settings = cog_settings.get("purchase", {})
            cost = purchase_settings.get("cost", 10)
            max_purchase = purchase_settings.get("max", 5)
            count = self._clamp(count, 1, max_purchase)

            multiplier_settings = cog_settings.get("multiplier", {})
            max_multiplier = multiplier_settings.get("max", 100)
            # Clamp the multiplier to the max allowed
            # multiplier will increase the cost of the ticket linearly
            # e.g. if base cost is 100 tacos, and multiplier is 2, cost is 200 tacos
            multiplier = self._clamp(multiplier, 1, max_multiplier)

            tickets_total_cost = cost * count * multiplier

            ticket_word = "ticket" if count == 1 else "tickets"
            taco_word = "taco" if tickets_total_cost == 1 else "tacos"
            user_taco_word = "taco" if user_taco_count == 1 else "tacos"

            if not self._validate_user_can_purchase(guild_id, user_id, tickets_total_cost):
                await self._send_message(
                    ctx,
                    self.settings.get_string(
                        guild_id,
                        "pulltab_purchase_not_enough_tacos",
                        total_cost=tickets_total_cost,
                        user=user.mention,
                        taco_word=taco_word,
                        ticket_count=count,
                        ticket_word=ticket_word,
                        user_taco_count=user_taco_count,
                        user_taco_word=user_taco_word,
                    ),
                    ephemeral=True,
                )
                return

            probabilities: typing.List[typing.Dict[str, typing.Any]] = cog_settings.get("probabilities", [])

            if len(probabilities) == 0:
                self.log.warn(
                    guild_id, f"{self._module}.{self._class}.{_method}", "No pulltab probabilities configured for guild"
                )
                return

            purchase_message = self.settings.get_string(
                guildId=guild_id,
                key="pulltab_purchase_message",
                ticket_word=ticket_word,
                ticket_count=count,
                multiplier=multiplier,
                total_cost=tickets_total_cost,
                taco_word=taco_word,
            )

            await self._send_message(ctx, purchase_message, ephemeral=True, followup=False)

            await asyncio.sleep(1)  # brief pause to ensure message order
            # generate a random code for the pulltab sequence
            # the code should be alphanumeric
            # the code should be 8 - 16 characters long
            # the code should be unique
            # store the code in self.ticket_codes
            # tickets_output = []
            for _ in range(count):
                ticket_code, ticket_output = self._generate_ticket(
                    guild_id=guild_id, user_id=user_id, cog_settings=cog_settings, multiplier=multiplier
                )
                view = self._create_ticket_view(ctx, code=ticket_code, multiplier=multiplier)
                await self._send_message(ctx, message=ticket_output, followup=True, view=view, ephemeral=True)
                # pause briefly to avoid rate limits
                await asyncio.sleep(1)

            await self.taco_helper.give_tacos(
                guildId=guild_id,
                fromUser=self.bot.user,
                toUser=user,
                taco_amount=(tickets_total_cost * -1),
                reason=self.settings.get_string(
                    guildId=guild_id,
                    key="pulltab_purchase_tacos_message",
                    ticket_word=ticket_word,
                    ticket_count=count,
                    multiplier=multiplier,
                ),
                give_type=TacoTypes.PULLTAB_PURCHASE,
            )

        except Exception as e:
            await self.message_helper.notify_of_error(ctx)
            self.log.error(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"Error processing pulltab purchase: {e}",
                traceback.format_exc(),
            )

    async def _process_pulltab_redeem(self, ctx: typing.Union[commands.Context, Interaction], *, code: str) -> None:
        _method = inspect.stack()[0][3]
        guild_id: int = 0
        user_id: int = 0
        try:
            # Defer interaction immediately to avoid 3-second timeout
            if isinstance(ctx, Interaction) and not ctx.response.is_done():
                await ctx.response.defer(ephemeral=True)

            if not code:
                # code not provided, just exit
                return
            from_user = self.bot.user
            if from_user is None:
                self.log.warn(guild_id, f"{self._module}.{self._class}.{_method}", "Bot user not found")
                return
            if isinstance(ctx, commands.Context):
                guild_id = ctx.guild.id if ctx.guild else 0
                user_id = ctx.author.id
            elif isinstance(ctx, Interaction):
                guild_id = ctx.guild.id if ctx.guild else 0
                user_id = ctx.user.id

            to_user = await self.entity_helper.get_or_fetch_user(user_id)
            if to_user is None:
                self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", "Could not fetch user")
                return

            success, reward, message = self._redeem_ticket(guild_id=guild_id, user_id=user_id, code=code)
            if success and reward > 0:
                await self.taco_helper.give_tacos(
                    guildId=guild_id,
                    fromUser=from_user,
                    toUser=to_user,
                    taco_amount=reward,
                    give_type=TacoTypes.PULLTAB_REDEEM,
                    reason=self.settings.get_string(guild_id, "pulltab_give_tacos_message"),
                )
                await self._send_message(ctx, message=message, ephemeral=True, followup=True)
            else:
                await self._send_message(ctx, message=message, ephemeral=True, followup=True)
        except Exception as e:
            await self.message_helper.notify_of_error(ctx)
            self.log.error(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"Error processing pulltab purchase: {e}",
                traceback.format_exc(),
            )

    def _generate_ticket(
        self, *, guild_id: int, user_id: int, cog_settings: typing.Dict[str, typing.Any], multiplier: int
    ) -> typing.Tuple[str, str]:
        """Generate a pulltab ticket.
        Returns a tuple of (code: str, ticket_output: str)
        """
        _method = inspect.stack()[0][3]
        code = ""
        ticket_output = ""
        while not code or code in self.ticket_codes_cache:
            code = self.identity_helper.id(min=8, max=16)

        probabilities: typing.List[typing.Dict[str, typing.Any]] = cog_settings.get("probabilities", [])
        symbols = [p['symbol'] for p in probabilities]
        weights = [p['weight'] for p in probabilities]

        purchase_settings = cog_settings.get("purchase", {})
        cost = purchase_settings.get("cost", 10)
        ticket_cost = cost * multiplier

        ticket_settings = cog_settings.get("ticket", {})
        rows = ticket_settings.get("rows", 5)
        cols = ticket_settings.get("columns", 3)

        # multiplier settings may be present at the top level (cog_settings["multiplier"])
        # or nested under purchase (cog_settings["purchase"]["multiplier"]) depending
        # on how the guild config is authored. Try both to be resilient to either style.
        multiplier_settings = cog_settings.get("multiplier", {})
        base_increase = multiplier_settings.get("base_increase", 0.5)
        max_multiplier = multiplier_settings.get("max", 100)
        # Clamp the multiplier to the max allowed
        # multiplier will increase the cost of the ticket linearly
        # e.g. if base cost is 100 tacos, and multiplier is 2, cost is 200 tacos
        multiplier = self._clamp(multiplier, 1, max_multiplier)

        # calculate the effective multiplier for the ticket
        # This is the multiplier that will be used to calculate the reward
        # if the base_increase is 0.5, and the multiplier is 2, the calculated multiplier is 1 + (0.5 * (2 - 1)) = 1.5
        # if the base_increase is 0.5, and the multiplier is 5, the calculated multiplier is 1 + (0.5 * (5 - 1)) = 3.0
        # if the base_increase is 0, the calculated multiplier is always 1
        # if the multiplier is 1, the calculated multiplier is always 1
        effective_multiplier = self._calculate_multiplier(multiplier, base_increase=base_increase)

        ticket = []
        random.seed(code)
        sheet = random.choices(symbols, weights=weights, k=rows * cols)
        for r in range(rows):
            row_list = sheet[r * cols : (r + 1) * cols]
            # store ticket rows as strings (e.g. '🍎🍊🍎') to match DB expectations
            row_str = "".join(row_list)
            ticket.append(row_str)

        self._save_ticket(
            guild_id=guild_id,
            user_id=user_id,
            code=code,
            ticket=ticket,
            cog_settings=cog_settings,
            cost=ticket_cost,
            purchase_multiplier=multiplier,
            effective_multiplier=effective_multiplier,
        )

        sheet_display = ""
        for row_index, row in enumerate(ticket):
            # row may be a string or a list; ensure we join individual symbols for display
            sheet_display += "||" + "  ".join(list(row)) + "||\n"

        # get the ticket output
        ticket_output = f"ticket: ||`{code}`||\n\n{sheet_display}\n"

        return code, ticket_output

    def _save_ticket(
        self,
        *,
        guild_id: int,
        user_id: int,
        code: str,
        ticket: typing.List[str],
        cog_settings: typing.Dict[str, typing.Any],
        redeemed_at: typing.Optional[int] = None,
        purchase_multiplier: float = 1.0,
        cost: int = 10,
        effective_multiplier: float = 1.0,
    ):
        """Save a pulltab ticket to storage."""
        _method = inspect.stack()[0][3]

        # store also winning line indexes from the ticket processing
        is_winner, reward, lines = self._process_ticket(
            ticket=ticket, cog_settings=cog_settings, effective_multiplier=effective_multiplier
        )

        ticket_entry = PullTabTicketEntry(
            guild_id=guild_id,
            user_id=user_id,
            code=code,
            ticket=ticket,
            redeemed_at=redeemed_at,
            reward=reward,
            winning_lines=lines if lines else None,
            cost=cost,
            purchase_multiplier=purchase_multiplier,
            effective_multiplier=effective_multiplier,
        )

        self.pulltabs_db.save_ticket(ticket_entry.to_dict())

        # the code is unique, and the ticket has been generated, store the code in the cache
        # the code is used to identify the pulltab sequence
        # to redeem the pulltab sequence, the user must provide the code
        self.ticket_codes_cache.add(code)

    def _process_ticket(
        self, *, ticket: typing.List[str], cog_settings: typing.Dict[str, typing.Any], effective_multiplier: float = 1.0
    ) -> typing.Tuple[bool, int, typing.List[typing.Dict[str, int]]]:
        """Process a pulltab ticket.
        Returns a tuple of (
            is_winner: bool,
            reward: int,
            winning_lines: list[dict[str, int]], # [{line: reward}]
            calculated_multiplier: float
        )
        Matching rules are tested by exact sequence or by token counts (so '🌮🌮' matches if
        there are two tacos anywhere in the row). When multiple rules for the same symbol
        match the row, only the highest reward for that symbol is awarded to avoid
        double-counting (e.g., a triple taco will not also claim a single- and double-
        taco payout).
        The multiplier parameter is applied to line rewards after the line's base reward is calculated.
        """

        probabilities: typing.List[typing.Dict[str, typing.Any]] = cog_settings.get("probabilities", [])

        total_reward = 0
        is_winner = False
        winning_lines: typing.List[typing.Dict[str, int]] = []

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

        for row_index, row in enumerate(ticket):
            # ticket rows are stored as strings (e.g. '🍎🍊🍎'); convert to list of symbols
            # Note: legacy nested lists are no longer expected; if found, attempt to flatten
            if isinstance(row, str):
                row_symbols = list(row)
            elif isinstance(row, list):
                # legacy fallback - convert list of symbols to chars
                row_symbols = list("".join(row))
            else:
                # unexpected row type - coerce to string then to symbol list
                row_symbols = list(str(row))
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
                    # this should always be 1, unless a deny rule is configured; if multiplier is 0 the whole row is a losing line
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
            for _sym, line_reward, match_str, _mult in row_matches:
                actual_line_reward = round(line_reward * effective_multiplier)
                # each line is its own winner; allow the same match message to appear multiple times
                total_reward += actual_line_reward
                is_winner = True if actual_line_reward > 0 else is_winner

                winning_lines.append({match_str: actual_line_reward})

        return is_winner, total_reward, winning_lines

    def _redeem_ticket(self, guild_id: int, user_id: int, code: str) -> typing.Tuple[bool, int, str]:
        """Redeem a pulltab ticket.
        Returns a tuple of (success: bool, reward: int, message: str)
        """
        _method = inspect.stack()[0][3]

        ticket = self.pulltabs_db.get_ticket(guild_id, user_id, code)
        if not ticket:
            return False, 0, self.settings.get_string(guild_id, "pulltab_redeem_invalid_code")

        if ticket.redeemed_at is not None:
            return False, 0, self.settings.get_string(guild_id, "pulltab_redeem_already_redeemed", code=code)

        # Mark the ticket as redeemed even if there is no reward
        self.pulltabs_db.update_ticket(guild_id, user_id, code, {"redeemed_at": int(utils.get_timestamp())})

        if ticket.reward is None or ticket.reward <= 0:
            return True, 0, self.settings.get_string(guild_id, "pulltab_redeem_success_no_reward", code=code)

        taco_word = "taco" if ticket.reward == 1 else "tacos"

        return (
            True,
            ticket.reward,
            self.settings.get_string(
                guild_id, "pulltab_redeem_success_with_reward", code=code, reward=ticket.reward, taco_word=taco_word
            ),
        )

    def _validate_user_can_purchase(self, guild_id: int, user_id: int, total_cost: int) -> bool:
        """Validate that a user has enough tacos to purchase pulltab tickets."""
        _method = inspect.stack()[0][3]
        taco_count = self.taco_helper.get_taco_count(guild_id, user_id)
        if taco_count is None:
            self.log.error(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"Could not retrieve taco count for user {user_id} in guild {guild_id}",
            )
            return False
        return taco_count >= total_cost

    def _clamp(self, count: int, min_value: int, max_value: int) -> int:
        if count < min_value:
            return min_value
        if count > max_value:
            return max_value
        return count

    def _calculate_multiplier(self, requested_multiplier: int = 1, base_increase: float = 0.05) -> float:
        """Calculate the effective multiplier based on requested multiplier points."""
        requested_multiplier = self._clamp(requested_multiplier, 1, 100)
        if requested_multiplier == 1:
            return 1.0
        if base_increase <= 0:
            return 1.0
        # Example calculation: each multiplier point increases the effective multiplier by <base_increase>
        # Historically this calculated increase used (requested_multiplier - 1) which meant
        # buying multiplier=10 with base_increase=0.1 resulted in 1.9. Users expect the
        # base_increase to apply per point, so multiplier=10 should result in 2.0.
        calculated_multiplier = 1 + (requested_multiplier * base_increase)
        return calculated_multiplier

    async def _send_message(self, ctx: typing.Union[commands.Context, discord.Interaction], message: str, **kwargs):
        _method = inspect.stack()[0][3]
        if isinstance(ctx, commands.Context):
            # remove ephemeral from kwargs if present, as Context.send does not support it
            if 'ephemeral' in kwargs:
                kwargs.pop('ephemeral')
            if 'followup' in kwargs:
                kwargs.pop('followup')
            await ctx.send(message, **kwargs)
        elif isinstance(ctx, Interaction):
            # Check if we should use followup (either explicitly requested or response already sent)
            use_followup = kwargs.pop('followup', False) or ctx.response.is_done()

            if use_followup:
                await ctx.followup.send(message, **kwargs)
            else:
                await ctx.response.send_message(message, **kwargs)
        else:
            guild_id = ctx.guild.id if ctx.guild else 0
            self.log.error(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"Invalid context type for sending message: cannot send message: {message}",
            )

    def _create_ticket_view(
        self, ctx: typing.Union[commands.Context, Interaction], *, code: str, multiplier: int = 1
    ) -> discord.ui.View:
        """Create a Discord button for redeeming a pulltab ticket."""
        return PullTabTicketRedeemView(ctx=ctx, code=code, multiplier=multiplier, settings=self.settings, cog=self)


async def setup(bot: TacoBot):
    settings = Settings()
    message_helper = MessageHelper(bot, settings)
    identity_helper = IdentityHelper()
    entity_helper = EntityHelper(bot)
    permissions = Permissions(bot, settings)
    pulltabs_db = PullTabTicketsDatabase()
    taco_helper = TacoHelper(bot, entity_helper=entity_helper)
    await bot.add_cog(
        PullTabCog(
            bot=bot,
            settings=settings,
            message_helper=message_helper,
            permissions=permissions,
            identity_helper=identity_helper,
            entity_helper=entity_helper,
            taco_helper=taco_helper,
            pulltabs_db=pulltabs_db,
        )
    )
