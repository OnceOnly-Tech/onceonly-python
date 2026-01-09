import os
import time
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)
key = "ai:job:example:poll-status"

# Start/attach
run = client.ai.run(key=key, ttl=120, metadata={"demo": True})
print("run status:", run.status, "version:", run.version, "lease:", run.lease_id)

# Poll using backend hint retry_after_sec
while True:
    st = client.ai.status(key)
    print("status:", st.status, "ttl_left:", st.ttl_left, "retry_after:", st.retry_after_sec, "ver:", st.version)
    if st.status in ("completed", "failed"):
        break
    sleep_s = st.retry_after_sec or 1
    time.sleep(max(1, min(10, int(sleep_s))))

out = client.ai.result(key)
print("result status:", out.status)
print("result:", out.result)
print("error_code:", out.error_code)
