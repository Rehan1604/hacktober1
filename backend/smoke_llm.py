import asyncio

from app.llm import get_provider


async def main():
    p = get_provider()
    print("health:", await p.health())
    print("---")
    async for chunk in p.stream(
        "You explain documents in plain, simple English for a worried reader.",
        "Explain in 2 sentences: HbA1c 6.8% (ref 4.0-5.6)",
    ):
        print(chunk, end="", flush=True)
    print()


asyncio.run(main())