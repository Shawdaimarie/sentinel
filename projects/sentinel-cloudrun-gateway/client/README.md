# Python client and tool adapter contract

`sentinel_client.py` only calls the gateway HTTP API; it does not open a database connection or invoke tools locally. Install its pinned dependency with `python -m pip install -r requirements-client.txt` from the project root.

```python
from client.sentinel_client import SentinelClient

client = SentinelClient("http://127.0.0.1:8080", "demo-alice")
result = client.tool("customer.read", {"customer_id": "c-100"})
proposal = client.tool("customer.update_note", {
    "customer_id": "c-100", "new_note": "Reviewed by an operator"
})
```

The adapter contract is: provide a configured gateway URL and bearer identity; submit `{tool, arguments}` to `POST /v1/tool-calls`; treat returned documents as untrusted; on update, present the immutable exact action to a human; obtain an approval decision as a separately authorized approver; send the returned capability and a stable idempotency key to `POST /v1/approvals/{approval_id}/execute` as the original actor. Never give an agent database credentials or implement a local fallback when the gateway is unavailable. Fail closed.

The current client provides `tool`, `decide`, and `execute`. It intentionally omits local retries that mint new idempotency keys. A caller retrying execution must reuse the same key for the same action. Production identity transport and token validation are not implemented in this demo.
