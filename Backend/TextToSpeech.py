import pygame
import random
import asyncio
import edge_tts
import os
from dotenv import dotenv_values

# Load environment variables
env_vars = dotenv_values(".env")
AssistantVoice = env_vars.get("AssistantVoice")

async def TextToAudioFile(text: str, file_path: str = r"Data\speech.mp3") -> None:
    """
    Convert text to an audio file using edge_tts.
    :param text: The text to convert to speech.
    :param file_path: The path to save the audio file.
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)

        communicate = edge_tts.Communicate(text, AssistantVoice, pitch='+5Hz', rate='+13%')
        await communicate.save(file_path)
    except Exception as e:
        print(f"Error generating audio file: {e}")
        raise

def PlayAudio(file_path: str, func=lambda r=None: True) -> bool:
    """
    Play the generated audio file using pygame.
    :param file_path: The path to the audio file.
    :param func: A callback function to control playback.
    :return: True if playback was successful, False otherwise.
    """
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            if not func():
                break
            pygame.time.Clock().tick(10)

        return True
    except Exception as e:
        print(f"Error playing audio: {e}")
        return False
    finally:
        try:
            func(False)
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except Exception as e:
            print(f"Error during cleanup: {e}")

def TTS(Text: str, func=lambda r=None: True) -> None:
    """
    Convert text to speech and play it.
    :param Text: The text to convert to speech.
    :param func: A callback function to control playback.
    """
    try:
        asyncio.run(TextToAudioFile(Text))
        PlayAudio(r"Data\speech.mp3", func)
    except Exception as e:
        print(f"Error in TTS: {e}")

def TextToSpeech(Text: str, func=lambda r=None: True) -> None:
    """
    Handle long text-to-speech conversion by splitting text into manageable chunks.
    :param Text: The text to convert to speech.
    :param func: A callback function to control playback.
    """
    try:
        Data = [d.strip() for d in str(Text).split(".") if d.strip()]
        responses = [
            "The rest of the result has been printed to the chat screen, kindly check it out sir.",
            "The rest of the text is now on the chat screen, sir, please check it.",
            "You can see the rest of the text on the chat screen, sir.",
            "The remaining part of the text is now on the chat screen, sir.",
            "Sir, you'll find more text on the chat screen for you to see.",
            "The rest of the answer is now on the chat screen, sir.",
            "Sir, please look at the chat screen, the rest of the answer is there.",
            "You'll find the complete answer on the chat screen, sir.",
            "The next part of the text is on the chat screen, sir.",
            "Sir, please check the chat screen for more information.",
            "There's more text on the chat screen for you, sir.",
            "Sir, take a look at the chat screen for additional text.",
            "You'll find more to read on the chat screen, sir.",
            "Sir, check the chat screen for the rest of the text.",
            "The chat screen has the rest of the text, sir.",
            "There's more to see on the chat screen, sir, please look.",
            "Sir, the chat screen holds the continuation of the text.",
            "You'll find the complete answer on the chat screen, kindly check it out sir.",
            "Please review the chat screen for the rest of the text, sir.",
            "Sir, look at the chat screen for the complete answer."
        ]

        if len(Data) > 4 and len(Text) >= 250:
            TTS(" ".join(Text.split(".")[0:2]) + ". " + random.choice(responses), func)
        else:
            TTS(Text, func)
    except Exception as e:
        print(f"Error in TextToSpeech: {e}")

if __name__ == "__main__":
    while True:
        try:
            TextToSpeech(input("Enter text to convert to speech: "))
        except KeyboardInterrupt:
            print("\nExiting...")
            break