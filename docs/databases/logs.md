# logs

This document describes the structure of the `logs` collection used in TacoBot. Each document represents a log entry for events or errors in a Discord guild.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **guild_id**: *(string)*  
  The Discord guild (server) ID.
- **timestamp**: *(number)*  
  The time the log entry was created (epoch).
- **level**: *(string)*  
  The log level (e.g., "info", "error").
- **method**: *(string)*  
  The method or function where the log was generated.
- **message**: *(string)*  
  The log message.
- **stack_trace**: *(string)*  
  The stack trace if the log is an error.

## Example

```json
{
  "_id": "ObjectId('...')",
  "guild_id": "123456789012345678",
  "timestamp": 1693459200,
  "level": "error",
  "method": "onMessage",
  "message": "Unhandled exception occurred.",
  "stack_trace": "Traceback..."
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "LogEntry",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "guild_id": { "type": "string", "description": "Discord guild/server ID" },
    "timestamp": { "type": "number", "description": "Epoch timestamp" },
    "level": { "type": "string", "description": "Log level" },
    "method": { "type": "string", "description": "Method or function name" },
    "message": { "type": "string", "description": "Log message" },
    "stack_trace": { "type": "string", "description": "Stack trace" }
  },
  "required": ["_id", "guild_id", "timestamp", "level", "method", "message"]
}
```
