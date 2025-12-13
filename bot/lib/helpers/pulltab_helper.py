import inspect
import random
import typing
from collections import Counter

from bot.lib import utils
from bot.lib.helpers import IdentityHelper, Numbers
from bot.lib.models.PullTabRedeemedTicket import PullTabRedeemedTicket
from bot.lib.models.PullTabTicketEntry import PullTabTicketEntry
from bot.lib.mongodb.pulltabs import PullTabTicketsDatabase
from bot.lib.settings import Settings
from bot.tacobot import TacoBot


class PullTabHelper:
    def __init__(self, bot: TacoBot, identity_helper: IdentityHelper, pulltabs_db: PullTabTicketsDatabase, settings: Settings):
        self.bot = bot
        self.identity_helper = identity_helper
        self.pulltabs_db = pulltabs_db
        self.settings = settings
        self.ticket_codes_cache: typing.Set[str] = set()

    def generate_ticket(
        self, *, guild_id: int, user_id: int, cog_settings: typing.Dict[str, typing.Any], multiplier: int
    ) -> typing.Tuple[str, PullTabTicketEntry]:
        """Generate a pulltab ticket.
        Returns a tuple of (code: str, ticket_output: str)
        """
        _method = inspect.stack()[0][3]
        code = ""
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
        multiplier = int(Numbers.clamp(multiplier, 1, max_multiplier))

        # calculate the effective multiplier for the ticket
        # This is the multiplier that will be used to calculate the reward
        # if the base_increase is 0.5, and the multiplier is 2, the calculated multiplier is 1 + (0.5 * (2 - 1)) = 1.5
        # if the base_increase is 0.5, and the multiplier is 5, the calculated multiplier is 1 + (0.5 * (5 - 1)) = 3.0
        # if the base_increase is 0, the calculated multiplier is always 1
        # if the multiplier is 1, the calculated multiplier is always 1
        effective_multiplier = self.calculate_multiplier(multiplier, base_increase=base_increase)

        ticket: typing.List[str] = []
        random.seed(code)
        sheet = random.choices(symbols, weights=weights, k=rows * cols)
        for r in range(rows):
            row_list = sheet[r * cols : (r + 1) * cols]
            # store ticket rows as strings (e.g. '🍎🍊🍎') to match DB expectations
            row_str = "".join(row_list)
            ticket.append(row_str)

        ticket_entry = self._save_ticket(
            guild_id=guild_id,
            user_id=user_id,
            code=code,
            ticket=ticket,
            cog_settings=cog_settings,
            cost=ticket_cost,
            purchase_multiplier=multiplier,
            effective_multiplier=effective_multiplier,
        )

        # get the ticket output
        # ticket_output = f"ticket: ||`{code}`||\n\n{sheet_display}\n"

        return code, ticket_entry

    def process_ticket(
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

    def redeem_ticket(self, guild_id: int, user_id: int, code: str) -> PullTabRedeemedTicket:
        """Redeem a pulltab ticket.
        Returns a tuple of (success: bool, reward: int, message: str)
        """
        _method = inspect.stack()[0][3]

        ticket = self.pulltabs_db.get_ticket(guild_id, user_id, code)
        if not ticket:
            return PullTabRedeemedTicket(
                success=False,
                reward=0,
                message=self.settings.get_string(guild_id, "pulltab_redeem_invalid_code"),
                ticket=None,
            )

        if ticket.redeemed_at is not None:
            return PullTabRedeemedTicket(
                success=False,
                reward=0,
                message=self.settings.get_string(guild_id, "pulltab_redeem_already_redeemed", code=code),
                ticket=ticket,
            )

        # Mark the ticket as redeemed even if there is no reward
        redeemed_at = int(utils.get_timestamp())
        updated_ticket = self.pulltabs_db.update_ticket(guild_id, user_id, code, {"redeemed_at": redeemed_at})
        if updated_ticket:
            ticket = updated_ticket

        if ticket.reward is None or ticket.reward <= 0:
            return PullTabRedeemedTicket(
                success=True,
                reward=0,
                message=self.settings.get_string(guild_id, "pulltab_redeem_success_no_reward", code=code),
                ticket=ticket,
            )

        taco_word = "taco" if ticket.reward == 1 else "tacos"

        return PullTabRedeemedTicket(
            success=True,
            reward=ticket.reward,
            message=self.settings.get_string(
                guild_id, "pulltab_redeem_success_with_reward", code=code, reward=ticket.reward, taco_word=taco_word
            ),
            ticket=ticket,
        )

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
    ) -> PullTabTicketEntry:
        """Save a pulltab ticket to storage."""
        _method = inspect.stack()[0][3]

        # store also winning line indexes from the ticket processing
        is_winner, reward, lines = self.process_ticket(
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
        return ticket_entry

    def calculate_multiplier(self, requested_multiplier: int = 1, base_increase: float = 0.05) -> float:
        """Calculate the effective multiplier based on requested multiplier points."""
        requested_multiplier = int(Numbers.clamp(requested_multiplier, 1, 100))
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

    def get_pending_tickets_for_user(self, *, guild_id: int, user_id: int) -> typing.List[PullTabTicketEntry]:
        """Get pull tab tickets for a user in a guild."""
        tickets_data = self.pulltabs_db.get_pending_tickets_for_user(guild_id, user_id)
        tickets = [PullTabTicketEntry.from_dict(data) for data in tickets_data]
        return tickets
