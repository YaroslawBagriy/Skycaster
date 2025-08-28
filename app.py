import os
import re
import json
from typing import Optional, Dict, Any, List

from dotenv import load_dotenv
from openai import OpenAI

from prompts import SYSTEM_PROMPT, ONE_SHOT_USER, ONE_SHOT_ASSISTANT
from weather_providers import get_weather

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------- Tool schema (Chat Completions API) ----------
chat_tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current or near-term weather for a city (and optional lat/lon).",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name, e.g., 'New York'"},
                    "lat":  {"type": "number", "description": "Latitude if available"},
                    "lon":  {"type": "number", "description": "Longitude if available"}
                },
                "required": ["city"]
            }
        }
    }
]

# ---------- Simple text → city extractor ----------
CITY_IN_UTTERANCE = re.compile(r"\b(?:in|for)\s+([A-Za-z .'\-]+)$", re.IGNORECASE)

def resolve_city(user_text: str, default_city: str) -> str:
    # "what's the weather in New York" → "New York"
    m = CITY_IN_UTTERANCE.search(user_text.strip())
    if m:
        return m.group(1).strip()
    return default_city

# ---------- Python function the model can call ----------
def tool_get_weather(args: Dict[str, Any]) -> Dict[str, Any]:
    city = args.get("city")
    lat  = args.get("lat")
    lon  = args.get("lon")
    res = get_weather(city=city, lat=lat, lon=lon)
    # ensure strictly serializable
    return {
        "city": res.get("city"),
        "temp_f": res.get("temp_f"),
        "condition": res.get("condition"),
        "precip_prob": res.get("precip_prob"),
        "when": res.get("when", "today"),
    }

# ---------- Main round-trip using Chat Completions ----------
def run(user_text: str, default_city: str,
        default_lat: Optional[float] = None,
        default_lon: Optional[float] = None) -> str:
    # Figure out which city to use
    resolved_city = resolve_city(user_text, default_city)

    # If the user didn’t specify a city, append the default city to the query
    if resolved_city == default_city and "in" not in user_text.lower():
        user_text = f"{user_text} in {default_city}"

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": ONE_SHOT_USER},
        {"role": "assistant", "content": ONE_SHOT_ASSISTANT},
        {"role": "user", "content": user_text},
    ]

    # 1) Ask model; it may request a tool call
    first = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=chat_tools,
        tool_choice="auto",
        temperature=0.2,
    )

    print("\nDEBUG First Response:\n",
          json.dumps(first.model_dump(), indent=2))
    
    choice = first.choices[0]
    msg = choice.message

    if not msg.tool_calls:
        txt = (msg.content or "").strip()
        return txt if txt else "Sorry, I had trouble answering."

    tool_messages: List[Dict[str, Any]] = []
    for tc in msg.tool_calls:
        fn_name = tc.function.name
        try:
            args = json.loads(tc.function.arguments or "{}")
        except Exception:
            args = {}

        args.setdefault("city", resolved_city)
        if default_lat is not None and default_lon is not None:
            args.setdefault("lat", default_lat)
            args.setdefault("lon", default_lon)

        if fn_name == "get_weather":
            result = tool_get_weather(args)
        else:
            result = {"error": f"Unknown tool {fn_name}"}

        print("\nresult: ", result)
        tool_messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "name": fn_name,
            "content": json.dumps(result)
        })

    followup = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            *messages,
            {"role": "assistant", "content": None, "tool_calls": msg.tool_calls},
            *tool_messages
        ],
        temperature=0.2,
    )

    print("\nDEBUG followup Response:\n",
          json.dumps(followup.model_dump(), indent=2))

    final_text = (followup.choices[0].message.content or "").strip()
    return final_text if final_text else "Sorry, I had trouble answering."


# ---------- CLI ----------
if __name__ == "__main__":
    default_city = os.getenv("DEFAULT_CITY", "Minneapolis, MN")
    default_lat = os.getenv("DEFAULT_LAT")
    default_lon = os.getenv("DEFAULT_LON")
    # cast if provided
    default_lat = float(default_lat) if default_lat is not None else None
    default_lon = float(default_lon) if default_lon is not None else None

    print("Type a question like: 'What's the weather today' or 'What's the weather in New York'")
    while True:
        try:
            q = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break
        if not q:
            continue
        if q.lower() in {"quit", "exit"}:
            print("Bye!")
            break
        try:
            print(run(q, default_city, default_lat, default_lon))
        except Exception as e:
            # Keep demo polished; avoid huge traces
            print(f"Sorry, something went wrong: {e.__class__.__name__}")