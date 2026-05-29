from dotenv import load_dotenv
load_dotenv()

import asyncio
from pipelines.idea2video_pipeline import Idea2VideoPipeline


# SET YOUR OWN IDEA, USER REQUIREMENT, AND STYLE HERE
idea = \
    """
A curious orange tabby cat explores a cozy old bookshop filled with towering shelves and warm golden lamplight.
The cat leaps between stacked books, knocks over a pile, and chases a dust mote caught in a sunbeam.
Between adventures, it curls up on an open novel by the window and purrs contentedly.
"""
user_requirement = \
    """
Do not exceed 3 scenes. Each scene should be no more than 5 shots.
"""
style = "Warm, storybook illustration style"


async def main():
    pipeline = Idea2VideoPipeline.init_from_config(
        config_path="configs/idea2video.yaml")
    await pipeline(idea=idea, user_requirement=user_requirement, style=style)

if __name__ == "__main__":
    asyncio.run(main())
