# Collection: trivia_questions

This collection stores trivia questions used in the TacoBot trivia game. Each document represents a single trivia question and its metadata.

## Document Structure
- `_id`: ObjectId
- `guild_id`: String
- `channel_id`: String
- `message_id`: String
- `question_id`: String
- `starter_id`: String
- `question`: String
- `correct_answer`: String
- `incorrect_answers`: Array of Strings
- `category`: String
- `difficulty`: String
- `reward`: Number
- `punishment`: Number
- `correct_users`: Array of Strings
- `incorrect_users`: Array of Strings
- `timestamp`: Number

## Example Document
```json
{
  "_id": "ObjectId(...)" ,
  "guild_id": "1234567890",
  "channel_id": "9876543210",
  "message_id": "5555555555",
  "question_id": "q1",
  "starter_id": "1111111111",
  "question": "What is the capital of France?",
  "correct_answer": "Paris",
  "incorrect_answers": ["London", "Berlin", "Rome"],
  "category": "Geography",
  "difficulty": "easy",
  "reward": 5,
  "punishment": -2,
  "correct_users": ["1111111111"],
  "incorrect_users": ["2222222222"],
  "timestamp": 1693449600
}
```


## JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TriviaQuestions",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId" },
    "guild_id": { "type": "string" },
    "channel_id": { "type": "string" },
    "message_id": { "type": "string" },
    "question_id": { "type": "string" },
    "starter_id": { "type": "string" },
    "question": { "type": "string" },
    "correct_answer": { "type": "string" },
    "incorrect_answers": { "type": "array", "items": { "type": "string" } },
    "category": { "type": "string" },
    "difficulty": { "type": "string" },
    "reward": { "type": "number" },
    "punishment": { "type": "number" },
    "correct_users": { "type": "array", "items": { "type": "string" } },
    "incorrect_users": { "type": "array", "items": { "type": "string" } },
    "timestamp": { "type": "number" }
  },
  "required": ["_id", "guild_id", "channel_id", "message_id", "question_id", "starter_id", "question", "correct_answer", "incorrect_answers", "category", "difficulty", "reward", "punishment", "correct_users", "incorrect_users", "timestamp"]
}
```
