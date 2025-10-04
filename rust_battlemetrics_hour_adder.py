import subprocess
import sys
import os

def install_package(package):
    """Install a package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def check_and_install_dependencies():
    """Check and install required packages"""
    required_packages = {
        'keyboard': 'keyboard==0.13.5',
        'pyautogui': 'pyautogui==0.9.54'
    }
    
    missing_packages = []
    
    for package_name, package_spec in required_packages.items():
        try:
            __import__(package_name)
        except ImportError:
            missing_packages.append(package_spec)
    
    if missing_packages:
        print("Installing required packages...")
        for package in missing_packages:
            print(f"Installing {package}...")
            if install_package(package):
                print(f"[SUCCESS] {package} installed successfully")
            else:
                print(f"[ERROR] Failed to install {package}")
                print("Please install manually with: pip install " + package)
                input("Press Enter to continue anyway...")
        print("All packages installed!\n")

# Install dependencies before importing them
check_and_install_dependencies()

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import time
import threading
import json
import keyboard
import pyautogui
import winsound
import random
from datetime import datetime, timedelta

class RustAFKHourAdder:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Rust Battlemetrics AFK Hour Adder Tool")
        self.root.geometry("650x900")  # Increased height to show GitHub link and version
        self.root.resizable(True, True)  # Allow resizing so users can adjust if needed
        
        # Create data folder
        self.data_folder = "data"
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
        
        # Default settings
        self.settings = {
            "pause_time": 60,  # 1 minute in seconds
            "stealth_mode": False,  # Kill player after movement to prevent spectating
            "disable_first_disconnect": False,  # Option to disable first disconnect command
            "server_switching": {
                "enabled": False,
                "time_range": "2-3",  # hours
                "selected_servers": []  # indices of servers to rotate through
            }
        }
        
        self.selected_server = None
        self.is_running = False
        self.afk_thread = None
        self.start_time = None
        self.current_server_start_time = None
        self.next_server_switch_time = None
        
        # Initialize log file path
        self.log_file = os.path.join(self.data_folder, f"afk_log_{datetime.now().strftime('%Y%m%d')}.txt")
        
        # Load servers from separate file
        self.servers = self.load_servers()
        
        # Server filtering state
        self.server_filter = "all"  # "all", "premium", "non_premium"
        
        self.load_settings()
        self.create_gui()
    
    def load_servers(self):
        """Load servers from JSON file"""
        servers_file = os.path.join(self.data_folder, "servers.json")
        try:
            if os.path.exists(servers_file):
                with open(servers_file, "r") as f:
                    servers = json.load(f)
                    self.log_status(f"Loaded {len(servers)} servers from servers.json")
                    return servers
            else:
                # Create default servers file if it doesn't exist
                default_servers = [
                    {"name": "Rustafied.com US Long III", "ip": "uslong3.rustafied.com:28015", "premium": True},
                    {"name": "Rusty Moose US Medium", "ip": "medium.us.moose.gg:28010", "premium": True},
                    {"name": "Atlas - US 2X Monthly", "ip": "216.39.240.89:28010", "premium": False}
                ]
                self.save_servers(default_servers)
                self.log_status("Created default servers.json file")
                return default_servers
        except Exception as e:
            self.log_status(f"Error loading servers: {e}")
            # Return default servers as fallback
            return [
                {"name": "Rustafied.com US Long III", "ip": "uslong3.rustafied.com:28015", "premium": True},
                {"name": "Rusty Moose US Medium", "ip": "medium.us.moose.gg:28010", "premium": True},
                {"name": "Atlas - US 2X Monthly", "ip": "216.39.240.89:28010", "premium": False}
            ]
    
    def save_servers(self, servers=None):
        """Save servers to JSON file"""
        servers_file = os.path.join(self.data_folder, "servers.json")
        try:
            servers_to_save = servers if servers is not None else self.servers
            with open(servers_file, "w") as f:
                json.dump(servers_to_save, f, indent=2)
        except Exception as e:
            self.log_status(f"Error saving servers: {e}")
        
    def create_gui(self):
        # Title
        title_label = tk.Label(self.root, text="Rust Battlemetrics AFK Hour Adder Tool", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # Battlemetrics Hours Display
        self.hours_frame = tk.Frame(self.root)
        self.hours_frame.pack(pady=10)
        
        tk.Label(self.hours_frame, text="Battlemetrics Hours:", font=("Arial", 12)).pack()
        self.hours_label = tk.Label(self.hours_frame, text="00:00:00", font=("Arial", 14, "bold"), fg="green")
        self.hours_label.pack()
        
        # Server Selection
        server_frame = tk.LabelFrame(self.root, text="Server Management", padx=10, pady=10)
        server_frame.pack(pady=10, padx=20, fill="x")
        
        self.server_var = tk.StringVar()
        # Filter status label
        self.filter_status_label = tk.Label(server_frame, text="Showing: All Servers", 
                                           font=("Arial", 9), fg="blue")
        self.filter_status_label.pack(pady=(0, 5))
        
        self.server_listbox = tk.Listbox(server_frame, height=6)
        self.server_listbox.pack(fill="x", pady=5)
        
        server_buttons_frame = tk.Frame(server_frame)
        server_buttons_frame.pack(fill="x", pady=5)
        
        # First row of buttons
        buttons_row1 = tk.Frame(server_buttons_frame)
        buttons_row1.pack(fill="x", pady=2)
        
        tk.Button(buttons_row1, text="Add Server", command=self.add_server).pack(side="left", padx=5)
        tk.Button(buttons_row1, text="Remove Server", command=self.remove_server).pack(side="left", padx=5)
        
        # Second row of buttons
        buttons_row2 = tk.Frame(server_buttons_frame)
        buttons_row2.pack(fill="x", pady=2)
        
        tk.Button(buttons_row2, text="Hide Premium", command=self.hide_premium_servers).pack(side="left", padx=5)
        tk.Button(buttons_row2, text="Hide Non-Premium", command=self.hide_non_premium_servers).pack(side="left", padx=5)
        tk.Button(buttons_row2, text="Show All", command=self.show_all_servers).pack(side="left", padx=5)
        
        # Third row of buttons
        buttons_row3 = tk.Frame(server_buttons_frame)
        buttons_row3.pack(fill="x", pady=2)
        
        tk.Button(buttons_row3, text="Delete All Premium", command=self.delete_all_premium, bg="#8B0000", fg="white").pack(side="left", padx=5)
        tk.Button(buttons_row3, text="Delete All Non-Premium", command=self.delete_all_non_premium, bg="#8B0000", fg="white").pack(side="left", padx=5)
        
        # Settings
        settings_frame = tk.LabelFrame(self.root, text="Settings", padx=10, pady=10)
        settings_frame.pack(pady=10, padx=20, fill="x")
        
        pause_frame = tk.Frame(settings_frame)
        pause_frame.pack(fill="x", pady=5)
        
        tk.Label(pause_frame, text="AFK Loop Interval:").pack(side="left")
        self.pause_var = tk.StringVar(value="1 min")
        pause_dropdown = ttk.Combobox(pause_frame, textvariable=self.pause_var, 
                                     values=["1 min", "2 min", "5 min", "10 min"], 
                                     width=10, state="readonly")
        pause_dropdown.pack(side="right")
        
        # Stealth Mode Setting
        stealth_frame = tk.Frame(settings_frame)
        stealth_frame.pack(fill="x", pady=5)
        
        self.stealth_var = tk.BooleanVar(value=self.settings["stealth_mode"])
        stealth_checkbox = tk.Checkbutton(stealth_frame, text="Stealth Mode (Kill after movement - prevents spectating)", 
                                         variable=self.stealth_var, command=self.on_stealth_mode_change)
        stealth_checkbox.pack(anchor="w")
        
        # Disable First Disconnect Setting
        disconnect_frame = tk.Frame(settings_frame)
        disconnect_frame.pack(fill="x", pady=5)
        
        self.disable_disconnect_var = tk.BooleanVar(value=self.settings.get("disable_first_disconnect", False))
        disconnect_checkbox = tk.Checkbutton(disconnect_frame, text="Disable First Disconnect Command", 
                                           variable=self.disable_disconnect_var)
        disconnect_checkbox.pack(anchor="w")
        
        # Server Switching Settings
        switch_frame = tk.LabelFrame(settings_frame, text="Auto Server Switching", padx=5, pady=5)
        switch_frame.pack(fill="x", pady=5)
        
        self.switch_enabled_var = tk.BooleanVar(value=self.settings["server_switching"]["enabled"])
        tk.Checkbutton(switch_frame, text="Enable Auto Server Switching", 
                      variable=self.switch_enabled_var).pack(anchor="w")
        
        time_range_frame = tk.Frame(switch_frame)
        time_range_frame.pack(fill="x", pady=2)
        
        tk.Label(time_range_frame, text="Switch every:").pack(side="left")
        self.time_range_var = tk.StringVar(value=self.settings["server_switching"]["time_range"])
        time_range_combo = ttk.Combobox(time_range_frame, textvariable=self.time_range_var, 
                                       values=["1-2", "2-3", "3-6", "6-12"], width=10, state="readonly")
        time_range_combo.pack(side="left", padx=5)
        tk.Label(time_range_frame, text="hours").pack(side="left")
        
        tk.Button(switch_frame, text="Select Servers for Rotation", 
                 command=self.select_rotation_servers).pack(pady=5)
        
        # Control Buttons
        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=20)
        
        self.start_button = tk.Button(control_frame, text="Start Hour Farming", command=self.start_afk, 
                                     bg="green", fg="white", font=("Arial", 12, "bold"), width=15)
        self.start_button.pack(side="left", padx=10)
        
        self.stop_button = tk.Button(control_frame, text="Stop Hour Farming", command=self.stop_afk, 
                                    bg="#8B0000", fg="white", font=("Arial", 12, "bold"), width=15, state="disabled")
        self.stop_button.pack(side="left", padx=10)
        
        # Status
        self.status_label = tk.Label(self.root, text="Ready", font=("Arial", 10), fg="blue")
        self.status_label.pack(pady=(10, 5))
        
        # GitHub Link and Version
        github_frame = tk.Frame(self.root)
        github_frame.pack(pady=(5, 10))
        
        version_label = tk.Label(github_frame, text="v1.0.0", font=("Arial", 9), fg="gray")
        version_label.pack()
        
        github_link = tk.Label(github_frame, text="https://jlaiii.github.io/RUST-BM-AFK/", 
                              font=("Arial", 9), fg="blue", cursor="hand2")
        github_link.pack()
        github_link.bind("<Button-1>", lambda e: self.open_github_link())
        
        self.update_server_list()
        self.update_timer()
        
    def load_settings(self):
        settings_file = os.path.join(self.data_folder, "settings.json")
        try:
            if os.path.exists(settings_file):
                with open(settings_file, "r") as f:
                    saved_settings = json.load(f)
                    self.settings.update(saved_settings)
        except Exception as e:
            self.log_status(f"Error loading settings: {e}")
    
    def on_stealth_mode_change(self):
        """Handle stealth mode checkbox change"""
        if self.stealth_var.get():
            # When stealth mode is enabled, set AFK loop to 10 minutes
            self.pause_var.set("10 min")
    
    def save_settings(self):
        settings_file = os.path.join(self.data_folder, "settings.json")
        try:
            # Update settings from GUI
            self.settings["stealth_mode"] = self.stealth_var.get()
            self.settings["disable_first_disconnect"] = self.disable_disconnect_var.get()
            self.settings["server_switching"]["enabled"] = self.switch_enabled_var.get()
            self.settings["server_switching"]["time_range"] = self.time_range_var.get()
            
            with open(settings_file, "w") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            self.log_status(f"Error saving settings: {e}")
    
    def log_status(self, message):
        """Log status messages to file and print to console"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_message + "\n")
        except Exception as e:
            print(f"Error writing to log file: {e}")
        
        print(log_message)
    
    def update_server_list(self):
        self.server_listbox.delete(0, tk.END)
        for i, server in enumerate(self.servers):
            # Apply filter
            if self.server_filter == "premium" and not server["premium"]:
                continue
            elif self.server_filter == "non_premium" and server["premium"]:
                continue
            
            premium_text = " (Premium)" if server["premium"] else ""
            self.server_listbox.insert(tk.END, f"{server['name']}{premium_text}")
    
    def add_server(self):
        dialog = ServerDialog(self.root)
        if dialog.result:
            self.servers.append(dialog.result)
            self.update_server_list()
            self.save_servers()
            self.log_status(f"Added server: {dialog.result['name']} ({dialog.result['ip']})")
    
    def remove_server(self):
        selection = self.server_listbox.curselection()
        if selection:
            # Get the actual server index considering current filter
            displayed_servers = self.get_filtered_servers()
            if selection[0] < len(displayed_servers):
                server_to_remove = displayed_servers[selection[0]]
                # Find the server in the main list
                for i, server in enumerate(self.servers):
                    if server['name'] == server_to_remove['name'] and server['ip'] == server_to_remove['ip']:
                        del self.servers[i]
                        break
                self.update_server_list()
                self.save_servers()
                self.log_status(f"Removed server: {server_to_remove['name']}")
    
    def get_filtered_servers(self):
        """Get list of servers based on current filter"""
        filtered = []
        for server in self.servers:
            if self.server_filter == "premium" and not server["premium"]:
                continue
            elif self.server_filter == "non_premium" and server["premium"]:
                continue
            filtered.append(server)
        return filtered
    
    def hide_premium_servers(self):
        """Hide premium servers from the list"""
        self.server_filter = "non_premium"
        self.update_server_list()
        self.filter_status_label.config(text="Showing: Non-Premium Servers Only")
        self.log_status("Hiding premium servers")
    
    def hide_non_premium_servers(self):
        """Hide non-premium servers from the list"""
        self.server_filter = "premium"
        self.update_server_list()
        self.filter_status_label.config(text="Showing: Premium Servers Only")
        self.log_status("Hiding non-premium servers")
    
    def show_all_servers(self):
        """Show all servers in the list"""
        self.server_filter = "all"
        self.update_server_list()
        self.filter_status_label.config(text="Showing: All Servers")
        self.log_status("Showing all servers")
    
    def delete_all_premium(self):
        """Delete all premium servers"""
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete ALL premium servers?\n\nThis action cannot be undone!"):
            premium_count = sum(1 for server in self.servers if server["premium"])
            self.servers = [server for server in self.servers if not server["premium"]]
            self.update_server_list()
            self.save_servers()
            self.log_status(f"Deleted {premium_count} premium servers")
            messagebox.showinfo("Success", f"Deleted {premium_count} premium servers")
    
    def delete_all_non_premium(self):
        """Delete all non-premium servers"""
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete ALL non-premium servers?\n\nThis action cannot be undone!"):
            non_premium_count = sum(1 for server in self.servers if not server["premium"])
            self.servers = [server for server in self.servers if server["premium"]]
            self.update_server_list()
            self.save_servers()
            self.log_status(f"Deleted {non_premium_count} non-premium servers")
            messagebox.showinfo("Success", f"Deleted {non_premium_count} non-premium servers")
    
    def select_rotation_servers(self):
        """Dialog to select which servers to include in rotation"""
        dialog = ServerRotationDialog(self.root, self.servers, 
                                     self.settings["server_switching"]["selected_servers"])
        if dialog.result is not None:
            self.settings["server_switching"]["selected_servers"] = dialog.result
            self.save_settings()
            self.log_status(f"Updated server rotation list: {len(dialog.result)} servers selected")
    
    def start_afk(self):
        # Validate settings
        try:
            pause_text = self.pause_var.get()
            if pause_text == "1 min":
                pause_minutes = 1
            elif pause_text == "2 min":
                pause_minutes = 2
            elif pause_text == "5 min":
                pause_minutes = 5
            elif pause_text == "10 min":
                pause_minutes = 10
            else:
                messagebox.showerror("Error", "Please select a valid AFK loop interval")
                return
            
            # If stealth mode is enabled, set AFK loop to 10 minutes
            if self.stealth_var.get():
                pause_minutes = 10
                self.pause_var.set("10 min")
                
            self.settings["pause_time"] = pause_minutes * 60
        except Exception:
            messagebox.showerror("Error", "Invalid AFK loop interval")
            return
        
        # Check server selection or rotation setup
        if self.switch_enabled_var.get():
            if not self.settings["server_switching"]["selected_servers"]:
                messagebox.showerror("Error", "Please select servers for rotation")
                return
            # Pick first server from rotation
            server_index = self.settings["server_switching"]["selected_servers"][0]
            self.selected_server = self.servers[server_index]
            self.setup_next_server_switch()
        else:
            selection = self.server_listbox.curselection()
            if not selection:
                messagebox.showerror("Error", "Please select a server")
                return
            # Get the actual server considering current filter
            displayed_servers = self.get_filtered_servers()
            if selection[0] < len(displayed_servers):
                self.selected_server = displayed_servers[selection[0]]
            else:
                messagebox.showerror("Error", "Invalid server selection")
                return
        
        # Show important popup message
        messagebox.showinfo("IMPORTANT", 
                           "You MUST tab into Rust after pressing OK!\n\n" +
                           "Press OK to continue and start the countdown.")
        
        # Start countdown
        self.is_running = True
        self.start_time = datetime.now()
        self.current_server_start_time = datetime.now()
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        
        self.log_status("=== Rust Hour Adder Started ===")
        self.log_status(f"Selected server: {self.selected_server['name']} ({self.selected_server['ip']})")
        self.log_status(f"Pause time: {pause_minutes} minutes")
        if self.switch_enabled_var.get():
            self.log_status(f"Auto server switching enabled: {self.time_range_var.get()} hours")
        
        self.afk_thread = threading.Thread(target=self.countdown_and_start, daemon=True)
        self.afk_thread.start()
        
        self.save_settings()
    
    def setup_next_server_switch(self):
        """Setup the next server switch time"""
        time_range = self.time_range_var.get()
        min_hours, max_hours = map(int, time_range.split('-'))
        switch_hours = random.uniform(min_hours, max_hours)
        self.next_server_switch_time = datetime.now() + timedelta(hours=switch_hours)
        self.log_status(f"Next server switch in {switch_hours:.1f} hours at {self.next_server_switch_time.strftime('%H:%M:%S')}")
    
    def switch_to_next_server(self):
        """Switch to the next server in rotation"""
        if not self.settings["server_switching"]["selected_servers"]:
            return
        
        # Find current server index in rotation
        current_server_name = self.selected_server['name']
        rotation_servers = self.settings["server_switching"]["selected_servers"]
        
        # Pick a random different server from rotation
        available_servers = [i for i in rotation_servers if self.servers[i]['name'] != current_server_name]
        if not available_servers:
            available_servers = rotation_servers  # If only one server, use it
        
        next_server_index = random.choice(available_servers)
        self.selected_server = self.servers[next_server_index]
        self.current_server_start_time = datetime.now()
        
        self.log_status(f"Switching to server: {self.selected_server['name']} ({self.selected_server['ip']})")
        
        # Disconnect from current server first
        self.log_status("Opening console (F1)")
        pyautogui.press('f1')
        time.sleep(1)
        
        self.log_status("Typing: client.disconnect")
        self.human_type("client.disconnect")
        pyautogui.press('enter')
        time.sleep(1)
        
        self.log_status("Closing console (F1)")
        pyautogui.press('f1')
        time.sleep(2)  # Wait a bit before reconnecting
        
        # Setup next switch
        self.setup_next_server_switch()
    
    def countdown_and_start(self):
        # Countdown from 10
        for i in range(10, 0, -1):
            if not self.is_running:
                return
            self.status_label.config(text=f"Starting in {i}... Tab into game window!")
            self.log_status(f"Countdown: {i} seconds remaining")
            time.sleep(1)
        
        if not self.is_running:
            return
            
        # Beep to indicate start
        winsound.Beep(1000, 500)
        self.status_label.config(text="Hour Adder Running...")
        self.log_status("Rust Hour Adder started! (Beep sound played)")
        
        # Start the main AFK loop
        self.afk_loop()
    
    def afk_loop(self):
        cycle_count = 0
        while self.is_running:
            try:
                cycle_count += 1
                self.log_status(f"=== Starting Hour Farming Cycle #{cycle_count} ===")
                
                # Check if we need to switch servers
                if (self.switch_enabled_var.get() and self.next_server_switch_time and 
                    datetime.now() >= self.next_server_switch_time):
                    self.switch_to_next_server()
                
                # Step 1: Disconnect from current server first (if not disabled)
                if not self.settings.get("disable_first_disconnect", False):
                    self.log_status("Opening console (F1)")
                    pyautogui.press('f1')
                    time.sleep(1)
                    
                    self.log_status("Typing: client.disconnect")
                    self.human_type("client.disconnect")
                    pyautogui.press('enter')
                    time.sleep(0.5)
                    
                    # Step 2: Close F1 after disconnect
                    self.log_status("Closing console (F1)")
                    pyautogui.press('f1')
                    time.sleep(3)
                else:
                    self.log_status("Skipping first disconnect (disabled in settings)")
                    time.sleep(1)
                
                # Step 3: Open F1 and connect to target server
                self.log_status("Opening console (F1)")
                pyautogui.press('f1')
                time.sleep(1)
                
                connect_command = f"client.connect {self.selected_server['ip']}"
                self.log_status(f"Typing: {connect_command}")
                self.human_type(connect_command)
                pyautogui.press('enter')
                time.sleep(1)
                
                # Step 4: Close F1
                self.log_status("Closing console (F1)")
                pyautogui.press('f1')
                
                # Step 5: Wait 1 minute
                self.log_status("Waiting 1 minute after connection...")
                for second in range(60):  # 1 minute = 60 seconds
                    if not self.is_running:
                        return
                    
                    # Log every 30 seconds during this wait
                    if second > 0 and second % 30 == 0:
                        remaining_seconds = 60 - second
                        self.log_status(f"Connection wait: {remaining_seconds} seconds remaining")
                    
                    time.sleep(1)
                
                # Step 6: Open F1 and type respawn
                self.log_status("Opening console (F1)")
                pyautogui.press('f1')
                time.sleep(1)
                
                self.log_status("Typing: respawn")
                self.human_type("respawn")
                pyautogui.press('enter')
                time.sleep(0.5)
                
                # Step 7: Close F1
                self.log_status("Closing console (F1)")
                pyautogui.press('f1')
                
                # Step 8: Wait 5 seconds
                self.log_status("Waiting 5 seconds after respawn...")
                time.sleep(5)
                
                # Step 9: Press spacebar and W
                self.log_status("Pressing spacebar")
                pyautogui.press('space')
                time.sleep(1)
                
                self.log_status("Pressing and holding W key for 1 second")
                pyautogui.keyDown('w')
                time.sleep(1)
                pyautogui.keyUp('w')
                self.log_status("Released W key")
                
                # Stealth Mode: Kill player to prevent spectating
                if self.settings["stealth_mode"]:
                    self.log_status("Stealth Mode: Opening console (F1)")
                    pyautogui.press('f1')
                    time.sleep(1)
                    
                    self.log_status("Stealth Mode: Typing: kill")
                    self.human_type("kill")
                    pyautogui.press('enter')
                    time.sleep(0.5)
                    
                    self.log_status("Stealth Mode: Closing console (F1)")
                    pyautogui.press('f1')
                    self.log_status("Stealth Mode: Player killed to prevent spectating")
                
                # Wait for the specified pause time before next cycle
                pause_time = self.settings["pause_time"]
                self.log_status(f"Waiting {pause_time // 60} minutes {pause_time % 60} seconds before next cycle")
                
                for second in range(pause_time):
                    if not self.is_running:
                        return
                    
                    # Log every minute during pause
                    if second > 0 and second % 60 == 0:
                        remaining_minutes = (pause_time - second) // 60
                        self.log_status(f"Pause: {remaining_minutes} minutes remaining")
                    
                    time.sleep(1)
                    
            except Exception as e:
                error_msg = f"Error in hour farming loop: {e}"
                self.log_status(error_msg)
                time.sleep(1)
    
    def human_type(self, text):
        """Type text with human-like timing"""
        for char in text:
            if not self.is_running:
                return
            pyautogui.write(char)
            # Random delay between 0.05 and 0.15 seconds
            time.sleep(0.05 + (time.time() % 0.1))
    
    def stop_afk(self):
        self.is_running = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.status_label.config(text="Stopped")
        
        if self.start_time:
            total_time = datetime.now() - self.start_time
            hours, remainder = divmod(total_time.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.log_status(f"=== Rust Hour Adder Stopped ===")
            self.log_status(f"Total Battlemetrics hours added: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}")
            self.log_status("="*50)
    
    def open_github_link(self):
        """Open the GitHub link in the default web browser"""
        import webbrowser
        webbrowser.open("https://jlaiii.github.io/RUST-BM-AFK/")
        self.log_status("Opened GitHub link in browser")
    
    def update_timer(self):
        if self.is_running and self.start_time:
            elapsed = datetime.now() - self.start_time
            hours, remainder = divmod(elapsed.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            time_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
            self.hours_label.config(text=time_str)
        
        self.root.after(1000, self.update_timer)
    
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
    
    def on_closing(self):
        self.stop_afk()
        self.root.destroy()

class ServerDialog:
    def __init__(self, parent):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Server")
        self.dialog.geometry("450x280")  # Made larger to accommodate all elements
        self.dialog.resizable(True, True)  # Allow resizing
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.transient(parent)
        
        # Main content frame
        content_frame = tk.Frame(self.dialog)
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Name
        tk.Label(content_frame, text="Server Name:", font=("Arial", 10, "bold")).pack(pady=(0, 5))
        self.name_entry = tk.Entry(content_frame, width=50, font=("Arial", 10))
        self.name_entry.pack(pady=(0, 15))
        
        # IP
        tk.Label(content_frame, text="Server IP:", font=("Arial", 10, "bold")).pack(pady=(0, 5))
        self.ip_entry = tk.Entry(content_frame, width=50, font=("Arial", 10))
        self.ip_entry.pack(pady=(0, 15))
        
        # Premium checkbox
        self.premium_var = tk.BooleanVar()
        tk.Checkbutton(content_frame, text="Premium Server", variable=self.premium_var, 
                      font=("Arial", 10)).pack(pady=(0, 20))
        
        # Buttons
        button_frame = tk.Frame(content_frame)
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Add Server", command=self.add_server, 
                 bg="green", fg="white", font=("Arial", 10, "bold"), 
                 width=12, height=2).pack(side="left", padx=15)
        tk.Button(button_frame, text="Cancel", command=self.dialog.destroy, 
                 bg="gray", fg="white", font=("Arial", 10, "bold"), 
                 width=12, height=2).pack(side="left", padx=15)
        
        self.name_entry.focus()
    
    def add_server(self):
        name = self.name_entry.get().strip()
        ip = self.ip_entry.get().strip()
        
        if not name or not ip:
            messagebox.showerror("Error", "Please fill in all fields")
            return
        
        self.result = {
            "name": name,
            "ip": ip,
            "premium": self.premium_var.get()
        }
        
        self.dialog.destroy()

class ServerRotationDialog:
    def __init__(self, parent, servers, selected_indices):
        self.result = None
        self.servers = servers
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Select Servers for Rotation")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)
        self.dialog.grab_set()
        self.dialog.transient(parent)
        
        tk.Label(self.dialog, text="Select servers to include in rotation:", 
                font=("Arial", 12, "bold")).pack(pady=10)
        
        # Server list with checkboxes
        self.server_vars = []
        server_frame = tk.Frame(self.dialog)
        server_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Scrollable frame
        canvas = tk.Canvas(server_frame)
        scrollbar = ttk.Scrollbar(server_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        for i, server in enumerate(servers):
            var = tk.BooleanVar(value=i in selected_indices)
            self.server_vars.append(var)
            
            premium_text = " (Premium)" if server["premium"] else ""
            text = f"{server['name']}{premium_text}"
            
            tk.Checkbutton(scrollable_frame, text=text, variable=var, 
                          font=("Arial", 10)).pack(anchor="w", pady=2)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Buttons
        button_frame = tk.Frame(self.dialog)
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Select All", command=self.select_all).pack(side="left", padx=10)
        tk.Button(button_frame, text="Clear All", command=self.clear_all).pack(side="left", padx=10)
        tk.Button(button_frame, text="OK", command=self.save_selection).pack(side="left", padx=10)
        tk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side="left", padx=10)
    
    def select_all(self):
        for var in self.server_vars:
            var.set(True)
    
    def clear_all(self):
        for var in self.server_vars:
            var.set(False)
    
    def save_selection(self):
        selected = []
        for i, var in enumerate(self.server_vars):
            if var.get():
                selected.append(i)
        
        if not selected:
            messagebox.showerror("Error", "Please select at least one server")
            return
        
        self.result = selected
        self.dialog.destroy()

if __name__ == "__main__":
    try:
        app = RustAFKHourAdder()
        app.run()
    except Exception as e:
        print(f"Error starting application: {e}")
        input("Press Enter to exit...")