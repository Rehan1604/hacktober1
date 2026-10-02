import asyncio
import sys
import time
from pathlib import Path

from app.explain import explain, to_hindi
from app.llm import get_provider

SAMPLE = Path(__file__).parent.parent / "samples" / "sample_report.txt"


async def heartbeat(t0):
    while True:
        await asyncio.sleep(10)
        print(f"  ...still working ({time.time() - t0:.0f}s)", flush=True)


async def timed(label, coro):
    t0 = time.time()
    hb = asyncio.create_task(heartbeat(t0))
    try:
        return await coro
    finally:
        hb.cancel()
        print(f"{label} took {time.time() - t0:.1f}s", flush=True)


async def main():
    provider = get_provider()
    text = SAMPLE.read_text(encoding="utf-8")
    print("Explaining (1-3 min on CPU)...", flush=True)
    exp = await timed("explain", explain(text, provider))
    print(exp.model_dump_json(indent=2))
    if "--hindi" in sys.argv:
        print("Translating to Hindi...", flush=True)
        hv = await timed("hindi", to_hindi(exp, provider))
        print(hv.model_dump_json(indent=2))


asyncio.run(main())