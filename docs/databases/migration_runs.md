# migration_runs

This document describes the structure of the `migration_runs` collection used in TacoBot. Each document in this collection represents a migration module and its completion status.

## Document Structure

- **_id**: *(ObjectId)*  
  The unique identifier for the document.
- **module**: *(string)*  
  The name of the migration module.
- **completed**: *(boolean)*  
  Whether the migration has been completed.

## Example

```json
{
  "_id": "ObjectId('...')",
  "module": "add_new_field",
  "completed": true
}
```

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "MigrationRun",
  "type": "object",
  "properties": {
    "_id": { "type": "string", "description": "MongoDB ObjectId as a string" },
    "module": { "type": "string", "description": "Migration module name" },
    "completed": { "type": "boolean", "description": "Completion status" }
  },
  "required": ["_id", "module", "completed"]
}
```
