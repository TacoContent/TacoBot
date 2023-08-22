import sys
import os
import traceback
import glob
import typing
import json


class SuggestionStates():
    def __init__(self) -> None:
        self.ACTIVE = "ACTIVE"
        self.APPROVED = "APPROVED"
        self.REJECTED = "REJECTED"
        self.CLOSED = "CLOSED"
        self.IMPLEMENTED = "IMPLEMENTED"
        self.CONSIDERED = "CONSIDERED"
        self.DELETED = "DELETED"
        
class TextWithAttachments():
    def __init__(self, text, attachments) -> None:
        self.text = text
        self.attachments = attachments

class TriviaQuestion():
    def __init__(
            self,
            guild_id: int,
            channel_id: int,
            message_id: int,
            starter_id: int,
            question: str,
            correct_answer: str,
            incorrect_answers:
            typing.List[str],
            category: str,
            difficulty: int,
            reward: int = 0,
            punishment: int = 0,
            correct_users: typing.List[int] = [],
            incorrect_users: typing.List[int] = [],
            ) -> None:
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.message_id = message_id
        self.question_id = f"{guild_id}-{channel_id}-{message_id}"
        self.starter_id = starter_id
        self.question = question
        self.correct_answer = correct_answer
        self.incorrect_answers = incorrect_answers
        self.category = category
        self.difficulty = difficulty
        self.reward = reward
        self.punishment = punishment
        self.correct_users = correct_users
        self.incorrect_users = incorrect_users
