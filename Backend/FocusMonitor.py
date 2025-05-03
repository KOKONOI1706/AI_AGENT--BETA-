from pynput import mouse, keyboard
import time
import threading
import psutil
import re
from datetime import datetime, timedelta
import json
import os
from dotenv import dotenv_values
from Frontend.GUI import ShowTextToScreen
from Backend.TextToSpeech import TextToSpeech

# Load environment variables
env_vars = dotenv_values(".env")
Username = env_vars.get("Username")
Assistantname = env_vars.get("Assistantname")

# Configuration
class FocusConfig:
    # Time in seconds of inactivity to consider user might be distracted
    INACTIVITY_THRESHOLD = 60
    # Time in seconds between focus checks
    CHECK_INTERVAL = 30
    # Work apps that indicate productive focus
    WORK_APPS = [
        'excel', 'word', 'powerpoint', 'outlook', 'teams', 'slack', 
        'chrome', 'edge', 'firefox', 'code', 'pycharm', 'jupyter',
        'notepad', 'terminal', 'cmd', 'powershell'
    ]
    # Distracting apps that indicate loss of focus
    DISTRACTION_APPS = [
        'youtube', 'netflix', 'facebook', 'instagram', 'twitter',
        'tiktok', 'reddit', 'game', 'discord', 'messenger'
    ]
    # Work time definition (24-hour format)
    WORK_START_TIME = '09:00'
    WORK_END_TIME = '17:00'
    # Days of the week for work (0=Monday, 6=Sunday)
    WORK_DAYS = [0, 1, 2, 3, 4]  # Monday to Friday
    
    # Path to store focus data
    FOCUS_DATA_PATH = os.path.join('Data', 'focus_data.json')
    # Path to store focus schedule
    FOCUS_SCHEDULE_PATH = os.path.join('Data', 'focus_schedule.json')

class FocusMonitor:
    def __init__(self):
        self.last_activity_time = time.time()
        self.focus_active = False
        self.mouse_listener = None
        self.keyboard_listener = None
        self.reminder_thread = None
        self.current_focus_start = None
        self.distraction_count = 0
        self.focus_data = self._load_focus_data()
        self.user_schedule = self._load_schedule()
        self.reminder_sent = False
        
    def _load_focus_data(self):
        """Load focus tracking data from file"""
        if os.path.exists(FocusConfig.FOCUS_DATA_PATH):
            try:
                with open(FocusConfig.FOCUS_DATA_PATH, 'r') as file:
                    return json.load(file)
            except json.JSONDecodeError:
                return {"sessions": [], "distractions": [], "stats": {"total_focus_time": 0}}
        return {"sessions": [], "distractions": [], "stats": {"total_focus_time": 0}}
    
    def _save_focus_data(self):
        """Save focus tracking data to file"""
        os.makedirs(os.path.dirname(FocusConfig.FOCUS_DATA_PATH), exist_ok=True)
        with open(FocusConfig.FOCUS_DATA_PATH, 'w') as file:
            json.dump(self.focus_data, file)
    
    def _load_schedule(self):
        """Load user's focus schedule"""
        if os.path.exists(FocusConfig.FOCUS_SCHEDULE_PATH):
            try:
                with open(FocusConfig.FOCUS_SCHEDULE_PATH, 'r') as file:
                    return json.load(file)
            except json.JSONDecodeError:
                return {"work_hours": {"start": FocusConfig.WORK_START_TIME, "end": FocusConfig.WORK_END_TIME}, 
                        "work_days": FocusConfig.WORK_DAYS}
        return {"work_hours": {"start": FocusConfig.WORK_START_TIME, "end": FocusConfig.WORK_END_TIME}, 
                "work_days": FocusConfig.WORK_DAYS}

    def _save_schedule(self):
        """Save user's focus schedule"""
        os.makedirs(os.path.dirname(FocusConfig.FOCUS_SCHEDULE_PATH), exist_ok=True)
        with open(FocusConfig.FOCUS_SCHEDULE_PATH, 'w') as file:
            json.dump(self.user_schedule, file)

    def update_schedule(self, start_time=None, end_time=None, work_days=None):
        """Update the user's work schedule"""
        schedule = self._load_schedule()
        
        if start_time:
            schedule["work_hours"]["start"] = start_time
        if end_time:
            schedule["work_hours"]["end"] = end_time
        if work_days is not None:
            schedule["work_days"] = work_days
            
        self.user_schedule = schedule
        self._save_schedule()
        return "Work schedule updated successfully."

    def _on_activity(self, *args):
        """Update the last activity timestamp when user interacts"""
        self.last_activity_time = time.time()
        self.reminder_sent = False
        
    def is_work_hours(self):
        """Check if current time is within defined work hours"""
        now = datetime.now()
        weekday = now.weekday()
        
        # Check if today is a work day
        if weekday not in self.user_schedule["work_days"]:
            return False
            
        # Parse work hours
        work_start = datetime.strptime(self.user_schedule["work_hours"]["start"], "%H:%M").time()
        work_end = datetime.strptime(self.user_schedule["work_hours"]["end"], "%H:%M").time()
        current_time = now.time()
        
        return work_start <= current_time <= work_end
        
    def is_productive_app(self, app_name):
        """Check if the current app is a productive one"""
        app_name = app_name.lower()
        
        # Check if app is in work apps list
        for work_app in FocusConfig.WORK_APPS:
            if work_app in app_name:
                return True
                
        # Check if app is in distraction apps list
        for distraction_app in FocusConfig.DISTRACTION_APPS:
            if distraction_app in app_name:
                return False
                
        # Default to considering unknown apps as neutral
        return None
        
    def get_active_window_title(self):
        """Get the title of the active window (platform-dependent)"""
        try:
            import win32gui
            window = win32gui.GetForegroundWindow()
            return win32gui.GetWindowText(window)
        except ImportError:
            # Fallback to using process information
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'].endswith('.exe'):
                        return proc.info['name']
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            return "Unknown"
    
    def _check_focus(self):
        """Check if user is focused on work"""
        current_time = time.time()
        
        # Skip check if not during work hours
        if not self.is_work_hours():
            return True
            
        # Check for extended inactivity
        if current_time - self.last_activity_time > FocusConfig.INACTIVITY_THRESHOLD:
            if not self.reminder_sent:
                self._send_reminder("I notice you haven't been active. Are you still working?")
                self.reminder_sent = True
            return False
            
        # Check active window
        active_window = self.get_active_window_title()
        app_productive = self.is_productive_app(active_window)
        
        if app_productive is False:  # Definitely distracting app
            if not self.reminder_sent:
                self._send_reminder(f"I notice you're using {active_window}. Let's refocus on work.")
                self.reminder_sent = True
                self._log_distraction(active_window)
            return False
            
        return True
    
    def _send_reminder(self, message):
        """Send a focus reminder to the user"""
        full_message = f"{Assistantname} : {message}"
        ShowTextToScreen(full_message)
        TextToSpeech(message)
        self.distraction_count += 1
        
    def _log_focus_session(self, end_time):
        """Log a completed focus session"""
        if self.current_focus_start:
            duration = end_time - self.current_focus_start
            session = {
                "start": datetime.fromtimestamp(self.current_focus_start).isoformat(),
                "end": datetime.fromtimestamp(end_time).isoformat(),
                "duration_seconds": duration
            }
            self.focus_data["sessions"].append(session)
            self.focus_data["stats"]["total_focus_time"] += duration
            self._save_focus_data()
    
    def _log_distraction(self, app_name):
        """Log a distraction event"""
        distraction = {
            "timestamp": datetime.now().isoformat(),
            "app": app_name
        }
        self.focus_data["distractions"].append(distraction)
        self._save_focus_data()
    
    def focus_monitor_loop(self):
        """Main monitoring loop"""
        while self.focus_active:
            focused = self._check_focus()
            
            # If transitioning from unfocused to focused
            if focused and not self.current_focus_start:
                self.current_focus_start = time.time()
                
            # If transitioning from focused to unfocused
            elif not focused and self.current_focus_start:
                self._log_focus_session(time.time())
                self.current_focus_start = None
                
            time.sleep(FocusConfig.CHECK_INTERVAL)
    
    def start_monitoring(self):
        """Start focus monitoring"""
        if not self.focus_active:
            self.focus_active = True
            
            # Start input listeners
            self.mouse_listener = mouse.Listener(on_move=self._on_activity, 
                                              on_click=self._on_activity, 
                                              on_scroll=self._on_activity)
            self.keyboard_listener = keyboard.Listener(on_press=self._on_activity)
            
            self.mouse_listener.start()
            self.keyboard_listener.start()
            
            # Start monitoring thread
            self.reminder_thread = threading.Thread(target=self.focus_monitor_loop, daemon=True)
            self.reminder_thread.start()
            
            message = f"Focus monitoring started. I'll help you stay on track during work hours."
            ShowTextToScreen(f"{Assistantname} : {message}")
            TextToSpeech(message)
            
            return "Focus monitoring activated."
            
    def stop_monitoring(self):
        """Stop focus monitoring"""
        if self.focus_active:
            self.focus_active = False
            
            if self.current_focus_start:
                self._log_focus_session(time.time())
                self.current_focus_start = None
            
            # Stop listeners
            if self.mouse_listener:
                self.mouse_listener.stop()
            if self.keyboard_listener:
                self.keyboard_listener.stop()
                
            message = "Focus monitoring stopped."
            ShowTextToScreen(f"{Assistantname} : {message}")
            TextToSpeech(message)
            
            return "Focus monitoring deactivated."
    
    def get_focus_report(self):
        """Generate a report of focus time and distractions"""
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time()).timestamp()
        
        # Calculate today's focus time
        today_focus_time = 0
        for session in self.focus_data["sessions"]:
            session_start = datetime.fromisoformat(session["start"]).timestamp()
            if session_start >= today_start:
                today_focus_time += session["duration_seconds"]
        
        # Count today's distractions
        today_distractions = 0
        for distraction in self.focus_data["distractions"]:
            distraction_time = datetime.fromisoformat(distraction["timestamp"]).timestamp()
            if distraction_time >= today_start:
                today_distractions += 1
        
        hours = int(today_focus_time // 3600)
        minutes = int((today_focus_time % 3600) // 60)
        
        report = f"Today's focus summary:\n"
        report += f"- Focus time: {hours} hours and {minutes} minutes\n"
        report += f"- Distractions: {today_distractions} times\n"
        
        if today_focus_time > 0:
            productivity_score = max(0, min(100, 100 - (today_distractions * 5)))
            report += f"- Productivity score: {productivity_score}%\n"
            
            if productivity_score >= 80:
                report += "Great job staying focused today!"
            elif productivity_score >= 60:
                report += "You're doing well, but there's room for improvement."
            else:
                report += "Let's work on reducing distractions tomorrow."
        
        return report

# Create a global instance
focus_monitor = FocusMonitor()

def start_focus_monitoring():
    return focus_monitor.start_monitoring()

def stop_focus_monitoring():
    return focus_monitor.stop_monitoring()

def get_focus_report():
    return focus_monitor.get_focus_report()

def update_work_schedule(start_time=None, end_time=None, work_days=None):
    return focus_monitor.update_schedule(start_time, end_time, work_days)

if __name__ == "__main__":
    # Test the module
    print(start_focus_monitoring())
    time.sleep(60)
    print(get_focus_report())
    print(stop_focus_monitoring())