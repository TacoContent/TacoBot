from bot.lib.models.triviaquestion import TriviaQuestion


def test_trivia_question_fields():
    tr = TriviaQuestion(1, 2, 3, 4, "q", "a", ["b"], "cat", 2)
    assert tr.question_id == "1-2-3"
