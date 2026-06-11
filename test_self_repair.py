import asyncio
from aura_node import AuraSovereignNode
from aura_evolve import LiquidFlashEvolve

async def run_evaluation():
    print("[*] Initializing active node context...")
    node = AuraSovereignNode()

    # Initialize the database palace connection asynchronously
    await node.memory_palace.__aenter__()

    refactor_loop = LiquidFlashEvolve(node)

    # Define an intentional design optimization request
    target = "vsa_resonator"
    proposal = "Optimize the resonate loop to execute in-place binary multiplications instead of allocating arrays."

    print(f"\n[*] Dispatching speculative repair request for '{target}.py'...")
    report = await refactor_loop.sandbox_and_evaluate(target, proposal)

    print("\n====================================================================")
    print(" 🌐 CLOSED-LOOP SPECULATIVE OPTIMIZATION COMPLETED")
    print("====================================================================")
    print(report)
    print("====================================================================\n")

    await node.memory_palace.__aexit__(None, None, None)

if __name__ == "__main__":
    asyncio.run(run_evaluation())
