# 🌤️ Skycaster — AI Weather Assistant

Skycaster is a Python project that turns OpenAI’s API into a **Siri-like weather forecaster**.  
It demonstrates **prompt engineering, one-shot learning, function calling, and API integration** while remaining extendable for geocoding, GPS input, and fine-tuning.

---

## ✨ Features

- **Prompt Engineering + One-Shot Learning**  
  Carefully designed system prompt and example dialogue ensure consistent, Siri-like responses:
  > “In Denver today: 60°F, mostly cloudy, with a 10% chance of showers.”

- **Real Weather Data via `weather_providers.py`**  
  OpenAI **does not have live weather built in** — it will hallucinate if asked directly.  
  Instead, the model calls a Python tool (`get_weather`) that fetches:
  - **Mock data** (demo mode, always works, no API key needed).  
  - **Live data** from [Open-Meteo](https://open-meteo.com/) (when enabled).  
  This separation makes the assistant both **realistic** and **extensible**.

- **OpenAI API Integration**  
  Uses the modern **Responses API** — a unified endpoint for completions, function calling, and more:  
  - [Responses API vs Chat Completions](https://platform.openai.com/docs/guides/migrate-to-responses)  
  - [Function Calling Guide](https://platform.openai.com/docs/guides/function-calling)  
  - [Responses API Reference](https://platform.openai.com/docs/api-reference/responses)  

- **Natural Language Location Parsing**  
  Handles queries like:  
  - `What's the weather today?` → uses default city.  
  - `What's the weather in New York?` → extracts “New York” automatically.

- **Extensible Architecture**  
  - Swap in geocoding for GPS coordinates.  
  - Add support for Celsius vs Fahrenheit.  
  - Fine-tune for tighter style control.

---

## 📂 Project Structure

skycaster/
├─ app.py               # Main CLI app with OpenAI integration
├─ prompts.py           # System + one-shot examples (prompt engineering)
├─ weather_providers.py # Mock & live weather data providers (facts)
├─ requirements.txt     # Python dependencies
└─ .env                 # API key & config (not committed)

**Why `weather_providers.py`?**  
- LLMs (like GPT-4o) generate language but don’t know today’s actual weather.  
- `weather_providers.py` is the **factual layer**.  
- OpenAI handles **voice/tone**, while `weather_providers.py` ensures accuracy.  
- This design demonstrates how to combine **LLMs with real-world APIs**
