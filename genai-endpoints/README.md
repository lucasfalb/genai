# GenAI API Bruno Collection

## Response Envelope

JSON endpoints return a standard success envelope:

```json
{
  "status": "success",
  "message": "Optional human message",
  "data": {},
  "meta": {}
}
```

JSON errors return:

```json
{
  "status": "error",
  "error": {
    "code": "MACHINE_CODE",
    "message": "Human message"
  }
}
```

`details` appears only when the API has structured diagnostic data, for example validation errors.

SSE chat endpoints keep the `text/event-stream` response format.
