import os
import re
from dotenv import load_dotenv
from openai import OpenAI
from typing import Optional, Dict, Any
from prompts import SYSTEM_PROMPT, ONE_SHOT_USER, ONE_SHOT_ASSISTANT
from weather_providers import get_weather

load_dotenv()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ---- Tool definition (function calling) ----
def tool_get_weather(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool the model can call. You can later replace manual lat/lon with GPS geocoding.
    """
    city = args.get("city")
    lat  = args.get("lat")
    lon  = args.get("lon")
    result = get_weather(city=city, lat=lat, lon=lon)
    # Return strictly structured data so the model can format the final sentence.
    return {
        "city": result["city"],
        "temp_f": result["temp_f"],
        "condition": result["condition"],
        "precip_prob": result["precip_prob"],
        "when": result["when"],
    }

TOOLS = [
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
                    "lon":  {"type": "number", "description": "Longitude if available"},
                },
                "required": ["city"]
            }
        }
    }
]

# ---- Simple city extractor for 'What's the weather in X' ----
CITY_IN_UTTERANCE = re.compile(r"in\s+([A-Za-z\s\.\-']+)$", re.IGNORECASE)

def resolve_city(user_text: str, default_city: str) -> str:
    m = CITY_IN_UTTERANCE.search(user_text.strip())
    if m:
        return m.group(1).strip()
    # If user said just "What's the weather today", fall back to default_city
    return default_city

def run(user_text: str, default_city: str, default_lat: Optional[float]=None, default_lon: Optional[float]=None):
    # Resolve the city now; later, replace with GPS->geocode pipeline.
    city = resolve_city(user_text, default_city)

    # Compose input with a one-shot to guide style
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": ONE_SHOT_USER},
        {"role": "assistant", "content": ONE_SHOT_ASSISTANT},
        {"role": "user", "content": user_text},
    ]

    # Let the model decide whether to call the tool
    response = client.responses.create(
        model="gpt-4o-mini",
        input=messages,
        tools=TOOLS,
    )

    # If a tool call is requested, execute it, then send the tool result back
    tool_calls = [b for b in response.output if getattr(b, "type", "") == "tool_call"]
    if tool_calls:
        # We only defined one function, so handle the first call
        call = tool_calls[0]
        fn_name = call.tool_call.name
        args = call.tool_call.arguments  # dict

        # If the model didn't provide a city, use our resolver
        args.setdefault("city", city)
        if default_lat is not None and default_lon is not None:
            args.setdefault("lat", default_lat)
            args.setdefault("lon", default_lon)

        tool_result = tool_get_weather(args)

        # Send tool result back so model can craft the final Siri-style sentence
        response2 = client.responses.create(
            model="gpt-4o-mini",
            input=[
                *messages,
                {
                    "role": "tool",
                    "content": tool_result,
                    "tool_call_id": call.tool_call_id
                }
            ]
        )
        text_chunks = [b for b in response2.output if getattr(b, "type", "") == "message"]
        final_text = text_chunks[0].content[0].text.value if text_chunks else "Sorry, I had trouble formatting the weather."
        return final_text

    # If the model answered without tool call (e.g., mock or refusal), return as-is
    text_chunks = [b for b in response.output if getattr(b, "type", "") == "message"]
    return text_chunks[0].content[0].text.value if text_chunks else "Sorry, I had trouble answering."

if __name__ == "__main__":
    default_city = os.getenv("DEFAULT_CITY", "Minneapolis, MN")
    print("Type a question like: 'What's the weather today' or 'What's the weather in New York'")
    while True:
        q = input("> ").strip()
        if not q:
            continue
        if q.lower() in {"quit", "exit"}:
            break
        print(run(q, default_city))