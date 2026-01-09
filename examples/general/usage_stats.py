import os
from onceonly import OnceOnly

API_KEY = os.getenv("ONCEONLY_API_KEY")
if not API_KEY:
    raise SystemExit("Set ONCEONLY_API_KEY env var")

client = OnceOnly(api_key=API_KEY)

def print_section(title: str, data: dict) -> None:
    print(f"\n== {title} ==")
    for k in sorted(data.keys()):
        print(f"{k.ljust(28)}: {data[k]}")

def main() -> None:
    me = client.me()
    print_section("/me", me)

    usage = client.usage(kind="make")
    print_section("/usage?kind=make", usage)

if __name__ == "__main__":
    main()
