# Starter travel agent

A small command-line AI agent based on ideas from Microsoft's
[AI Agents for Beginners](https://github.com/microsoft/ai-agents-for-beginners) course,
running on Claude (`claude-opus-5-5`) through the Anthropic Python SDK.

## What it shows

| Course lesson | Where to look in `agent.py` |
|---|---|
| 4. Tool use | `TOOLS` (descriptions Claude reads) and `agent_turn` (the loop: ask Claude → run tools → send results → repeat) |
| 6. Trustworthy agents | `book_trip` asks you to approve before booking |
| 7. Planning | The system prompt asks for a numbered plan first |
| 13. Memory | `remember_preference` saves to `memory.json`, which is loaded next run |

Destinations and flights are sample data, so nothing real gets booked.

## Run it

```bash
cd starter-agent
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # from console.anthropic.com
python agent.py
```

Things to try:

- `I want a cheap beach trip for 5 nights`
- `My budget is $1000 and I live in Sydney. Remember that.`
- `What time is it in Kyoto right now?`

## Ideas for next steps

- Swap the sample data for a real flight or hotel API.
- Add a tool of your own: write a function, add its description to `TOOLS`, and add it to `TOOL_FUNCTIONS`.
- Lesson 8 (multi-agent): split into a planner agent and a booking agent.
