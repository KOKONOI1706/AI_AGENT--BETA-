from Frontend.GUI import (
    GraphicalUserInterface,
    SetAssistantStatus,
    ShowTextToScreen,
    TempDirectoryPath,
    SetMicrophoneStatus,
    AnswerModifier,
    QueryModifier,
    GetMicrophoneStatus,
    GetAssistantStatus)
from Backend.Model import FirstLayerDMM
from Backend.RealTimeSearchEngine import RealtimeSearchEngine
from Backend.Automation import Automation
from Backend.SpeechToText import SpeechRecognition
from Backend.Chatbot import ChatBot
from Backend.TextToSpeech import TextToSpeech
from dotenv import dotenv_values
from asyncio import run
from time import sleep
import subprocess
import threading
import json
import os
import sys
from Backend.FocusMonitor import start_focus_monitoring, stop_focus_monitoring, get_focus_report, update_work_schedule

# Update the Functions list in Main.py:
Functions = ["open", "close", "play", "system", "content", "google search", "youtube search", "focus"]

# Load environment variables
env_vars = dotenv_values(".env")
Username = env_vars.get("Username")
Assistantname = env_vars.get("Assistantname")
DefaultMessage = f'''{Username} : Hello {Assistantname}, How are you?
{Assistantname} : Welcome {Username}. I am doing well. How may I help you?'''
Functions = ["open", "close", "play", "system", "content", "google search", "youtube search"]

def initialize_environment():
    """Initialize the environment by resetting files and loading default data."""
    SetMicrophoneStatus("False")
    ShowTextToScreen("")
    reset_chat_log()
    integrate_chat_log()
    display_chats_on_gui()

def reset_chat_log():
    """Reset chat log if no chats are present."""
    try:
        with open(r'Data\ChatLog.json', "r", encoding='utf-8') as file:
            if len(file.read()) < 5:
                with open(TempDirectoryPath('Database.data'), 'w', encoding='utf-8') as db_file:
                    db_file.write("")
                with open(TempDirectoryPath('Responses.data'), 'w', encoding='utf-8') as resp_file:
                    resp_file.write(DefaultMessage)
    except FileNotFoundError:
        print("ChatLog.json not found. Creating a new one.")
        with open(r'Data\ChatLog.json', "w", encoding='utf-8') as file:
            json.dump([], file)

def integrate_chat_log():
    """Integrate chat log data into a formatted file."""
    try:
        with open(r'Data\ChatLog.json', 'r', encoding='utf-8') as file:
            chatlog_data = json.load(file)
        formatted_chatlog = ""
        for entry in chatlog_data:
            role = Username if entry["role"] == "user" else Assistantname
            formatted_chatlog += f"{role}: {entry['content']}\n"
        with open(TempDirectoryPath('Database.data'), 'w', encoding='utf-8') as file:
            file.write(AnswerModifier(formatted_chatlog))
    except Exception as e:
        print(f"Error integrating chat log: {e}")

def display_chats_on_gui():
    """Display chats on the GUI."""
    try:
        with open(TempDirectoryPath('Database.data'), "r", encoding='utf-8') as file:
            data = file.read()
        if data.strip():
            with open(TempDirectoryPath('Responses.data'), "w", encoding='utf-8') as file:
                file.write(data)
    except Exception as e:
        print(f"Error displaying chats on GUI: {e}")

def execute_task(decision):
    """Execute tasks based on the decision."""
    try:
        run(Automation(decision))
    except Exception as e:
        print(f"Error executing task: {e}")

def handle_image_generation(query):
    """Handle image generation tasks."""
    try:
        with open(r"Frontend\Files\ImageGeneration.data", "w") as file:
            file.write(f"{query}, True")
        subprocess.Popen(['python', r"Backend\ImageGeneration.py"], shell=False)
    except Exception as e:
        print(f"Error starting ImageGeneration.py: {e}")

def process_decision(decision):
    """Process the decision and execute appropriate actions."""
    general_queries = [q for q in decision if q.startswith("general")]
    realtime_queries = [q for q in decision if q.startswith("realtime")]
    image_queries = [q for q in decision if "generate" in q]

    if image_queries:
        handle_image_generation(image_queries[0])

    if general_queries or realtime_queries:
        merged_query = " and ".join([q.split(" ", 1)[1] for q in general_queries + realtime_queries])
        if realtime_queries:
            SetAssistantStatus("Searching...")
            answer = RealtimeSearchEngine(QueryModifier(merged_query))
        else:
            SetAssistantStatus("Thinking...")
            answer = ChatBot(QueryModifier(merged_query))
        ShowTextToScreen(f"{Assistantname} : {answer}")
        SetAssistantStatus("Answering...")
        TextToSpeech(answer)

def main_execution():
    """Main execution loop for handling user queries."""
    SetAssistantStatus("Listening...")
    query = SpeechRecognition()
    ShowTextToScreen(f"{Username} : {query}")
    SetAssistantStatus("Thinking...")
    decision = FirstLayerDMM(query)
    print(f"Decision: {decision}")
    process_decision(decision)

def first_thread():
    """Thread to continuously listen for microphone input."""
    while True:
        if GetMicrophoneStatus() == "True":
            main_execution()
        else:
            if "Available..." not in GetAssistantStatus():
                SetAssistantStatus("Available...")
            sleep(0.1)

def second_thread():
    """Thread to run the graphical user interface."""
    GraphicalUserInterface()
def process_decision(decision):
    """Process the decision and execute appropriate actions."""
    general_queries = [q for q in decision if q.startswith("general")]
    realtime_queries = [q for q in decision if q.startswith("realtime")]
    image_queries = [q for q in decision if "generate" in q]
    focus_queries = [q for q in decision if q.startswith("focus")]

    if image_queries:
        handle_image_generation(image_queries[0])

    if focus_queries:
        for query in focus_queries:
            command = query.split(" ", 1)[1]
            if "start" in command:
                answer = start_focus_monitoring()
            elif "stop" in command:
                answer = stop_focus_monitoring()
            elif "report" in command:
                answer = get_focus_report()
            elif "schedule" in command:
                # Parse schedule commands - this is a simple implementation
                if "from" in command and "to" in command:
                    parts = command.lower().split()
                    start_idx = parts.index("from") + 1
                    end_idx = parts.index("to") + 1
                    if start_idx < len(parts) and end_idx < len(parts):
                        start_time = parts[start_idx]
                        end_time = parts[end_idx]
                        answer = update_work_schedule(start_time=start_time, end_time=end_time)
                else:
                    answer = "Please specify work hours in the format: focus schedule from 9:00 to 17:00"
            else:
                answer = "Focus monitoring commands: start, stop, report, schedule"
            
            ShowTextToScreen(f"{Assistantname} : {answer}")
            SetAssistantStatus("Answering...")
            TextToSpeech(answer)

    if general_queries or realtime_queries:
        merged_query = " and ".join([q.split(" ", 1)[1] for q in general_queries + realtime_queries])
        if realtime_queries:
            SetAssistantStatus("Searching...")
            answer = RealtimeSearchEngine(QueryModifier(merged_query))
        else:
            SetAssistantStatus("Thinking...")
            answer = ChatBot(QueryModifier(merged_query))
        ShowTextToScreen(f"{Assistantname} : {answer}")
        SetAssistantStatus("Answering...")
        TextToSpeech(answer)
if __name__ == "__main__":
    initialize_environment()
    threading.Thread(target=first_thread, daemon=True).start()
    second_thread()