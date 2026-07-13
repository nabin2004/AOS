import asyncio

from final_final_graph import animation_graph, AnimationState


async def main():
    state = AnimationState(
        query="Teach me about the stochastic gradient descent algorithm in machine learning.",
        classification=None,
    )

    await animation_graph.run(state=state)

    # print(result)

if __name__ == "__main__":
    asyncio.run(main())