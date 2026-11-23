"""Starter travel agent, built on ideas from Microsoft's "AI Agents for Beginners".

Course lessons this file shows in practice:
  - Lesson 4, tool use:        Claude picks which Python function to call.
  - Lesson 6, trustworthy AI:  booking needs a "yes" from you first.
  - Lesson 7, planning:        the system prompt asks for a plan before acting.
  - Lesson 13, memory:         preferences are saved to memory.json between runs.

Run it:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=...      # your key from console.anthropic.com
    python agent.py
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import anthropic

MODEL = "claude-opus-5-5"
MEMORY_FILE = Path(__file__).with_name("memory.json")

SYSTEM_PROMPT = """You are a friendly travel agent.

How you work:
1. For any request with more than one step, first write a short numbered plan, then carry it out.
2. Use your tools for facts (destinations, prices, flights, local time). Never invent prices or flights.
3. Only call book_trip after the traveller has picked a specific destination and flight.
4. When the traveller tells you a lasting preference (budget, home city, likes and dislikes),
   save it with remember_preference.
5. Keep replies short and easy to read."""

# ---------------------------------------------------------------------------
# Sample data. In a real agent these would be calls to live travel APIs.
# ---------------------------------------------------------------------------

DESTINATIONS = {
    "Barcelona": {"country": "Spain", "tz": "Europe/Madrid", "style": "beach, food, architecture", "hotel_per_night": 140},
    "Kyoto": {"country": "Japan", "tz": "Asia/Tokyo", "style": "culture, temples, food", "hotel_per_night": 160},
    "Queenstown": {"country": "New Zealand", "tz": "Pacific/Auckland", "style": "adventure, mountains", "hotel_per_night": 180},
    "Bali": {"country": "Indonesia", "tz": "Asia/Makassar", "style": "beach, relaxing, budget", "hotel_per_night": 70},
    "Reykjavik": {"country": "Iceland", "tz": "Atlantic/Reykjavik", "style": "nature, northern lights", "hotel_per_night": 200},
}

FLIGHTS = {
    "Barcelona": [("TA101", "08:15", 820), ("TA105", "21:40", 690)],
    "Kyoto": [("TA210", "10:05", 1150), ("TA214", "23:30", 980)],
    "Queenstown": [("TA330", "06:50", 540)],
    "Bali": [("TA402", "13:20", 610), ("TA406", "19:55", 520)],
    "Reykjavik": [("TA515", "16:10", 1300)],
}

# ---------------------------------------------------------------------------
# Tools: plain Python functions plus a JSON description Claude reads.
# ---------------------------------------------------------------------------


def load_memory() -> dict:
    try:
        return json.loads(MEMORY_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def list_destinations(style: str = "") -> str:
    matches = {
        name: info for name, info in DESTINATIONS.items()
        if not style or style.lower() in info["style"]
    }
    if not matches:
        return f"No destinations match '{style}'. Styles available: " + "; ".join(
            sorted({s.strip() for i in DESTINATIONS.values() for s in i["style"].split(",")})
        )
    return json.dumps(matches, indent=2)


def search_flights(destination: str) -> str:
    flights = FLIGHTS.get(destination)
    if not flights:
        return f"No flights found to {destination}. Known destinations: {', '.join(FLIGHTS)}"
    return json.dumps(
        [{"flight": f, "departs": t, "price_usd": p} for f, t, p in flights], indent=2
    )


def get_local_time(destination: str) -> str:
    info = DESTINATIONS.get(destination)
    if not info:
        return f"Unknown destination {destination}."
    now = datetime.now(ZoneInfo(info["tz"]))
    return f"It is {now:%A %H:%M} in {destination}."


def remember_preference(key: str, value: str) -> str:
    memory = load_memory()
    memory[key] = value
    MEMORY_FILE.write_text(json.dumps(memory, indent=2))
    return f"Saved: {key} = {value}"


def book_trip(destination: str, flight: str, nights: int) -> str:
    info = DESTINATIONS.get(destination)
    match = next((f for f in FLIGHTS.get(destination, []) if f[0] == flight), None)
    if nights < 1:
        return "Cannot book: nights must be 1 or more."
    if not info or not match:
        return f"Cannot book: unknown destination or flight ({destination}, {flight})."
    total = match[2] + info["hotel_per_night"] * nights
    # Human in the loop (lesson 6): the agent cannot book without your yes.
    answer = input(
        f"\n  >> Approve booking {flight} to {destination}, {nights} nights, ${total}? [y/N] "
    )
    if answer.strip().lower() != "y":
        return "The traveller declined this booking. Ask what they would like to change."
    return f"Booked! Flight {flight} + {nights} nights in {destination}. Total ${total}. Ref TRIP-{flight}-{nights}"


TOOL_FUNCTIONS = {
    "list_destinations": list_destinations,
    "search_flights": search_flights,
    "get_local_time": get_local_time,
    "remember_preference": remember_preference,
    "book_trip": book_trip,
}

DEST_PROP = {"type": "string", "enum": list(DESTINATIONS), "description": "Destination city."}

TOOLS = [
    {
        "name": "list_destinations",
        "description": "List destinations with their style and hotel price per night. "
                       "Optionally filter by a style word such as 'beach' or 'adventure'.",
        "input_schema": {
            "type": "object",
            "properties": {"style": {"type": "string", "description": "Optional style word to filter by."}},
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_flights",
        "description": "Search available flights to a destination, with departure time and price in USD.",
        "input_schema": {
            "type": "object",
            "properties": {"destination": DEST_PROP},
            "required": ["destination"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_local_time",
        "description": "Get the current local time at a destination.",
        "input_schema": {
            "type": "object",
            "properties": {"destination": DEST_PROP},
            "required": ["destination"],
            "additionalProperties": False,
        },
    },
    {
        "name": "remember_preference",
        "description": "Save a lasting traveller preference so it is remembered next time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Short name, e.g. 'budget' or 'home_city'."},
                "value": {"type": "string", "description": "The preference value."},
            },
            "required": ["key", "value"],
            "additionalProperties": False,
        },
    },
    {
        "name": "book_trip",
        "description": "Book a flight and hotel. The traveller is asked to approve before anything is booked.",
        "input_schema": {
            "type": "object",
            "properties": {
                "destination": DEST_PROP,
                "flight": {"type": "string", "description": "Flight number from search_flights, e.g. TA101."},
                "nights": {"type": "integer", "description": "Number of hotel nights (1 or more)."},
            },
            "required": ["destination", "flight", "nights"],
            "additionalProperties": False,
        },
    },
]
for tool in TOOLS:
    tool["strict"] = True


def run_tool(name: str, tool_input: dict) -> tuple[str, bool]:
    """Run one tool. Returns (result text, is_error)."""
    func = TOOL_FUNCTIONS.get(name)
    if func is None:
        return f"Unknown tool {name}", True
    try:
        return func(**tool_input), False
    except Exception as exc:  # report the problem back to Claude instead of crashing
        return f"Tool error: {exc}", True


# ---------------------------------------------------------------------------
# The agent loop (lesson 4): ask Claude, run the tools it asks for, repeat.
# ---------------------------------------------------------------------------


def agent_turn(client: anthropic.Anthropic, messages: list) -> None:
    memory = load_memory()
    system = SYSTEM_PROMPT
    if memory:
        system += "\n\nWhat you remember about this traveller:\n" + json.dumps(memory, indent=2)

    while True:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=system,
            tools=TOOLS,
            messages=messages,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium"},
            # If a safety check declines a request, the API retries on a fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        # Keep the whole reply (including thinking and tool calls) in the history.
        messages.append({"role": "assistant", "content": response.content})

        for block in response.content:
            if block.type == "text" and block.text.strip():
                print(f"\nAgent: {block.text}")
            elif block.type == "tool_use":
                print(f"  [tool] {block.name}({json.dumps(block.input)})")

        if response.stop_reason == "refusal":
            print("\nAgent: Sorry, I can't help with that request.")
            return
        if response.stop_reason == "pause_turn":
            continue
        if response.stop_reason != "tool_use":
            return  # end_turn or max_tokens: Claude has finished this turn

        # Run every tool Claude asked for and send all the results back together.
        results = []
        for block in response.content:
            if block.type == "tool_use":
                text, is_error = run_tool(block.name, block.input)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": text,
                    "is_error": is_error,
                })
        messages.append({"role": "user", "content": results})


def main() -> None:
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    messages: list = []
    print("Travel agent ready. Try: 'I want a cheap beach trip for 5 nights'. Type 'quit' to exit.")
    while True:
        try:
            user = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user.lower() in {"quit", "exit"}:
            break
        if not user:
            continue
        start = len(messages)
        messages.append({"role": "user", "content": user})
        try:
            agent_turn(client, messages)
        except anthropic.AuthenticationError:
            print("No valid API key. Set ANTHROPIC_API_KEY and try again.")
            return
        except anthropic.RateLimitError:
            print("Rate limited. Wait a moment and try again.")
            del messages[start:]  # drop the failed turn so you can retry
        except anthropic.APIStatusError as exc:
            print(f"API error {exc.status_code}: {exc.message}")
            del messages[start:]  # drop the failed turn so you can retry
        except anthropic.APIConnectionError:
            print("Could not reach the API. Check your internet connection.")
            del messages[start:]  # drop the failed turn so you can retry


if __name__ == "__main__":
    main()
