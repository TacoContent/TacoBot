import asyncio
import inspect
import os
import traceback
import typing

import discord
from bot.lib.discord.ext.commands.TacobotCog import TacobotCog
from bot.lib.enums.permissions import TacoPermissions
from bot.lib.enums.tacotypes import TacoTypes
from bot.lib.helpers import EntityHelper, IdentityHelper, MessageHelper, Numbers, PullTabHelper, TacoHelper
from bot.lib.mongodb.pulltabs import PullTabTicketsDatabase
from bot.lib.mongodb.tracking import TrackingDatabase
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
        pulltab_helper: PullTabHelper,
        pulltabs_db: PullTabTicketsDatabase,
        tracking_db: TrackingDatabase,

    ):
        super().__init__(bot, "pulltab", settings)
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.message_helper = message_helper
        self.identity_helper = identity_helper
        self.entity_helper = entity_helper
        self.pulltab_helper = pulltab_helper
        self.taco_helper = taco_helper
        self.permissions = permissions
        self.pulltabs_db = pulltabs_db
        self.tracking_db = tracking_db
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

        if (
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

        self.tracking_db.track_command_usage(
            guildId=ctx.guild.id if ctx.guild else 0,
            channelId=ctx.channel.id if ctx.channel else None,
            userId=ctx.author.id,
            command="pulltab",
            subcommand="purchase",
            args=[{"type": "command"}, {"count": count, "multiplier": multiplier}],
        )

    @group.command(name="purchase", description="Purchase a pulltab ticket for a chance to win tacos!")
    async def purchase_interaction(self, interaction: Interaction, *, count: int = 1, multiplier: int = 1):
        await self._process_pulltab_purchase(interaction, count=count, multiplier=multiplier)

        self.tracking_db.track_command_usage(
            guildId=interaction.guild.id if interaction.guild else 0,
            channelId=interaction.channel_id if interaction.channel_id else None,
            userId=interaction.user.id,
            command="pulltab",
            subcommand="purchase",
            args=[{"type": "slash_command"}, {"count": count, "multiplier": multiplier}],
        )

    @pulltab.command(name="info", aliases=["i"], description="Get information about pulltab payouts and probabilities")
    async def info_command(self, ctx: commands.Context, *, multiplier: int = 1):
        await self._process_pulltab_info(ctx, multiplier=multiplier)

        self.tracking_db.track_command_usage(
            guildId=ctx.guild.id if ctx.guild else 0,
            channelId=ctx.channel.id if ctx.channel else None,
            userId=ctx.author.id,
            command="pulltab",
            subcommand="info",
            args=[{"type": "command"}, {"multiplier": multiplier}],
        )

    @group.command(name="info", description="Get information about pulltab payouts and probabilities")
    async def info_interaction(self, interaction: Interaction, multiplier: int = 1):
        await self._process_pulltab_info(interaction, multiplier=multiplier)

        self.tracking_db.track_command_usage(
            guildId=interaction.guild.id if interaction.guild else 0,
            channelId=interaction.channel_id if interaction.channel_id else None,
            userId=interaction.user.id,
            command="pulltab",
            subcommand="info",
            args=[{"type": "slash_command"}, {"multiplier": multiplier}],
        )

    @pulltab.command(name="redeem", aliases=["r"], description="Redeem pulltab ticket")
    async def redeem_command(self, ctx: commands.Context, *, code: str) -> None:
        await self._process_pulltab_redeem(ctx, code=code)

        self.tracking_db.track_command_usage(
            guildId=ctx.guild.id if ctx.guild else 0,
            channelId=ctx.channel.id if ctx.channel else None,
            userId=ctx.author.id,
            command="pulltab",
            subcommand="redeem",
            args=[{"type": "command"}, {"code": code}],
        )

    @group.command(name="redeem", description="Redeem pulltab ticket")
    async def redeem_interaction(self, interaction: Interaction, *, code: str) -> None:
        await self._process_pulltab_redeem(interaction, code=code)

        self.tracking_db.track_command_usage(
            guildId=interaction.guild.id if interaction.guild else 0,
            channelId=interaction.channel_id if interaction.channel_id else None,
            userId=interaction.user.id,
            command="pulltab",
            subcommand="redeem",
            args=[{"type": "slash_command"}, {"code": code}],
        )

    def _build_payout_message(self, cog_settings: typing.Dict[str, typing.Any], multiplier: int = 1) -> str:
        probabilities: typing.List[typing.Dict[str, typing.Any]] = cog_settings.get("probabilities", [])
        multiplier_settings = cog_settings.get("multiplier", {})

        base_increase = multiplier_settings.get("base_increase", 0.5)
        max_multiplier = multiplier_settings.get("max", 100)

        multiplier = int(Numbers.clamp(multiplier, 1, max_multiplier))

        effective_multiplier = self.pulltab_helper.calculate_multiplier(multiplier, base_increase=base_increase)

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
        effective_example = self.pulltab_helper.calculate_multiplier(multiplier, base_increase=base_increase)
        message_lines.append(
            f"  (Example: with multiplier {multiplier} and base increase {pct:.1f}%, effective = {effective_example:.2f} → a 100-taco line becomes ~{round(100 * effective_example)} tacos)\n"
        )
        example_mul2 = min(10, max(2, int(max_multiplier if max_multiplier < 10 else 10)))
        effective_example2 = self.pulltab_helper.calculate_multiplier(example_mul2, base_increase=base_increase)
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

            if (
                self.permissions.has_taco_permission(
                    guild_id, user, TacoPermissions.PULLTAB_NO_PURCHASE
                )
            ):
                # stop processing if the user does not have permission
                await self._send_message(
                    ctx,
                    self.settings.get_string(guild_id, "pulltab_purchase_no_permission", user=user.mention),
                    ephemeral=True,
                )
                return

            purchase_settings = cog_settings.get("purchase", {})
            cost = purchase_settings.get("cost", 10)
            max_purchase = purchase_settings.get("max", 5)
            count = int(Numbers.clamp(count, 1, max_purchase))

            multiplier_settings = cog_settings.get("multiplier", {})
            max_multiplier = multiplier_settings.get("max", 100)
            # Clamp the multiplier to the max allowed
            # multiplier will increase the cost of the ticket linearly
            # e.g. if base cost is 100 tacos, and multiplier is 2, cost is 200 tacos
            multiplier = int(Numbers.clamp(multiplier, 1, max_multiplier))

            tickets_total_cost = cost * count * multiplier

            ticket_word = "ticket" if count == 1 else "tickets"
            taco_word = "taco" if tickets_total_cost == 1 else "tacos"
            user_taco_word = "taco" if user_taco_count == 1 else "tacos"

            if not self.taco_helper.validate_user_can_spend(guild_id, user_id, tickets_total_cost):
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
                ticket_code, ticket_entry = self.pulltab_helper.generate_ticket(
                    guild_id=guild_id, user_id=user_id, cog_settings=cog_settings, multiplier=multiplier
                )
                ticket_output = "ticket: ||`" + ticket_code + "`||\n\n"
                for row_index, row in enumerate(ticket_entry.ticket):
                    # row may be a string or a list; ensure we join individual symbols for display
                    ticket_output += "||" + "  ".join(list(row)) + "||\n"

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

            if (
                self.permissions.has_taco_permission(
                    guild_id, to_user, TacoPermissions.PULLTAB_NO_REDEEM
                )
            ):
                # stop processing if the user does not have permission
                await self._send_message(
                    ctx,
                    self.settings.get_string(guild_id, "pulltab_redeem_no_permission", user=to_user.mention),
                    ephemeral=True,
                )
                return

            redeemed_ticket = self.pulltab_helper.redeem_ticket(guild_id=guild_id, user_id=user_id, code=code)
            if redeemed_ticket.success and redeemed_ticket.reward > 0:
                await self.taco_helper.give_tacos(
                    guildId=guild_id,
                    fromUser=from_user,
                    toUser=to_user,
                    taco_amount=redeemed_ticket.reward,
                    give_type=TacoTypes.PULLTAB_REDEEM,
                    reason=self.settings.get_string(guild_id, "pulltab_give_tacos_message"),
                )
                await self._send_message(ctx, message=redeemed_ticket.message, ephemeral=True, followup=True)
            else:
                await self._send_message(ctx, message=redeemed_ticket.message, ephemeral=True, followup=True)
        except Exception as e:
            await self.message_helper.notify_of_error(ctx)
            self.log.error(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"Error processing pulltab purchase: {e}",
                traceback.format_exc(),
            )

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
    pulltabs_db = PullTabTicketsDatabase()
    tracking_db = TrackingDatabase()
    pulltab_helper = PullTabHelper(bot, identity_helper=identity_helper, pulltabs_db=pulltabs_db, settings=settings)
    entity_helper = EntityHelper(bot)
    permissions = Permissions(bot, settings)
    taco_helper = TacoHelper(bot, entity_helper=entity_helper)
    await bot.add_cog(
        PullTabCog(
            bot=bot,
            settings=settings,
            message_helper=message_helper,
            permissions=permissions,
            identity_helper=identity_helper,
            entity_helper=entity_helper,
            pulltab_helper=pulltab_helper,
            taco_helper=taco_helper,
            pulltabs_db=pulltabs_db,
            tracking_db=tracking_db,
        )
    )
