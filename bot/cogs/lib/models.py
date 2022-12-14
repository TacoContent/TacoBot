import sys
import os
import traceback
import glob
import typing
import json

class SuggestionStates():
    def __init__(self):
        self.ACTIVE = "ACTIVE"
        self.APPROVED = "APPROVED"
        self.REJECTED = "REJECTED"
        self.CLOSED = "CLOSED"
        self.IMPLEMENTED = "IMPLEMENTED"
        self.CONSIDERED = "CONSIDERED"
        self.DELETED = "DELETED"
class TextWithAttachments():
    def __init__(self, text, attachments):
        self.text = text
        self.attachments = attachments
