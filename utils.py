import random


def randomize_wait() -> float:
    # change wait seconds here
    return random.uniform(1, 3)


def is_prompt_message(message: str) -> bool:
    prompts = ["hey yinlin", "hi yinlin", "hello yinlin"]
    for prompt in prompts:
        if message.lower().startswith(prompt):
            return True

    return False


def filter_bmp_characters(text: str) -> str:
    # Filter out non BMP characters (emojis etc.)
    return ''.join(char for char in text if ord(char) <= 0xFFFF)
