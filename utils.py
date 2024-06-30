import random


def randomize_wait():
    # change wait seconds here
    return random.uniform(1, 3)


def is_prompt_message(message: str) -> bool:
    prompts = ["hey jojo", "hi jojo", "hello jojo"]
    for prompt in prompts:
        if message.lower().startswith(prompt):
            return True

    return False
