"""Everything this companion claims, in one command: the article's snippet,
then the audited trace and the CHSH measurement.

    python run_all.py
"""
import asyncio

import bell_pair
import chsh_spread
import test_bell_pair


async def main() -> None:
    print("=" * 72)
    print("THE SNIPPET (bell_pair.py) - the article's code, verbatim")
    print("=" * 72)
    await bell_pair.main()
    print()
    await test_bell_pair.main()
    print()
    await chsh_spread.main()


if __name__ == "__main__":
    asyncio.run(main())
