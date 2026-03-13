"""Test which Claude model IDs are valid."""
import os
import sys

key = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ANTHROPIC_API_KEY", "")
if not key:
    print("No API key", flush=True)
    sys.exit(1)

import anthropic
client = anthropic.Anthropic(api_key=key)

for model in ["claude-sonnet-4-6-20250514", "claude-sonnet-4-20250514", "claude-sonnet-4-6"]:
    try:
        r = client.messages.create(model=model, max_tokens=10,
                                   messages=[{"role": "user", "content": "hi"}])
        print("%s: OK" % model, flush=True)
    except Exception as e:
        err = str(e)[:120]
        print("%s: %s" % (model, err), flush=True)
