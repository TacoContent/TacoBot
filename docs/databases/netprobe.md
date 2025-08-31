# netprobe

This document describes the structure of the `netprobe` collection used in TacoBot. Each document represents a network probe result or configuration.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **id**: *(string)*  
  The probe ID.
- **data**: *(object)*  
  Probe data (complex nested structure, see schema for details).
- **ttl**: *(number)*  
  Time to live for the probe data.
- **created_at**: *(number)*  
  When the probe was created (epoch).

## Example

```json
{
  "_id": "ObjectId('...')",
  "id": "probe-001",
  "data": { "probe": "ping", "modem": "modem1", ... },
  "ttl": 3600,
  "created_at": 1693459200
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Netprobe",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "id": { "type": "string" },
    "data": { "type": "object" },
    "ttl": { "type": "number" },
    "created_at": { "type": "number" }
  },
  "required": ["_id", "id", "data", "ttl", "created_at"]
}
```
