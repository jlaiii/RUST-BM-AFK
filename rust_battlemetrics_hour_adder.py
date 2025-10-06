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
        'pyautogui': 'pyautogui==0.9.54',
        'pygetwindow': 'pygetwindow==0.0.9',
        'psutil': 'psutil==5.9.0'
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

# Disable pyautogui failsafe to prevent accidental mouse movement from stopping the program
pyautogui.FAILSAFE = False

class RustAFKHourAdder:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Rust Battlemetrics AFK Hour Adder Tool")
        self.root.geometry("900x700")  # Wider and shorter
        self.root.resizable(True, True)  # Allow resizing so users can adjust if needed
        
        # Create data folder
        self.data_folder = "data"
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
        
        # Default settings
        self.settings = {
            "pause_time": 60,  # 1 minute in seconds
            "kill_after_movement": False,  # Kill player after movement to prevent spectating
            "disable_startup_disconnect": True,  # Option to disable initial disconnect command when starting
            "disable_beep": False,  # Option to disable beep sounds
            "minimal_activity": False,  # Option to enable minimal activity mode (25min + kill after movement)
            "auto_start_rust": False,  # Option to auto start Rust via Steam
            "rust_load_time": "1 min",  # How long to wait for Rust to load
            "connection_wait_time": "1 min",  # How long to wait for connection to stabilize
            "start_at_boot": False,  # Option to start farming at Windows startup
            "auto_restart_game": False,  # Option to auto restart game for updates
            "restart_interval": "6h",  # How often to restart the game
            "server_switching": {
                "enabled": False,
                "time_range": "1-2",  # hours
                "stealth_mode": False,  # Enable stealth mode (connect → kill → wait)
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
        # Main container with padding
        main_container = tk.Frame(self.root)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Top section - Title and Hours
        top_frame = tk.Frame(main_container)
        top_frame.pack(fill="x", pady=(0, 10))
        
        # Title
        title_label = tk.Label(top_frame, text="Rust Battlemetrics AFK Hour Adder Tool", 
                              font=("Arial", 16, "bold"))
        title_label.pack()
        
        # Hours display
        self.hours_frame = tk.Frame(top_frame)
        self.hours_frame.pack(pady=5)
        
        tk.Label(self.hours_frame, text="Battlemetrics Hours:", font=("Arial", 12)).pack()
        self.hours_label = tk.Label(self.hours_frame, text="00:00:00", 
                                   font=("Arial", 14, "bold"), fg="green")
        self.hours_label.pack()
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill="both", expand=True, pady=(0, 10))
        
        # Tab 1: Server Management
        self.create_server_tab()
        
        # Tab 2: Basic Settings
        self.create_basic_settings_tab()
        
        # Tab 3: Automation Settings
        self.create_automation_tab()
        
        # Tab 4: Server Switching
        self.create_server_switching_tab()
        
        # Tab 5: About
        self.create_about_tab()
        
        # Bottom section - Control buttons and status
        bottom_frame = tk.Frame(main_container)
        bottom_frame.pack(fill="x", pady=(10, 0))
        
        # Control Buttons
        control_frame = tk.Frame(bottom_frame)
        control_frame.pack(pady=(0, 10))
        
        self.start_button = tk.Button(control_frame, text="Start Hour Farming", command=self.start_afk, 
                                     bg="green", fg="white", font=("Arial", 12, "bold"), width=15)
        self.start_button.pack(side="left", padx=10)
        
        self.stop_button = tk.Button(control_frame, text="Stop Hour Farming", command=self.stop_afk, 
                                    bg="#8B0000", fg="white", font=("Arial", 12, "bold"), width=15, state="disabled")
        self.stop_button.pack(side="left", padx=10)
        
        # Reset Settings Button
        tk.Button(control_frame, text="Reset All Settings", 
                 command=self.reset_to_defaults, bg="#FF6B35", fg="white", 
                 font=("Arial", 10, "bold"), width=15).pack(side="left", padx=10)
        
        # Status
        self.status_label = tk.Label(bottom_frame, text="Ready", font=("Arial", 10), fg="blue")
        self.status_label.pack()
        
        # Links and Version
        links_frame = tk.Frame(bottom_frame)
        links_frame.pack(pady=5)
        
        version_label = tk.Label(links_frame, text="v1.0.0", font=("Arial", 9), fg="gray")
        version_label.pack()
        
        # Links container
        links_container = tk.Frame(links_frame)
        links_container.pack()
        
        github_link = tk.Label(links_container, text="GitHub", 
                              font=("Arial", 9), fg="blue", cursor="hand2")
        github_link.pack(side="left", padx=5)
        github_link.bind("<Button-1>", lambda e: self.open_github_link())
        
        discord_link = tk.Label(links_container, text="Discord", 
                               font=("Arial", 9), fg="blue", cursor="hand2")
        discord_link.pack(side="left", padx=5)
        discord_link.bind("<Button-1>", lambda e: self.open_discord_link())
        
        self.update_server_list()
        self.update_timer()
        
        # Set initial UI state based on stealth mode, minimal activity, and auto restart
        self.on_stealth_mode_change()
        self.on_minimal_activity_change()
        self.on_auto_restart_change()
    
    def create_server_tab(self):
        """Create the server management tab"""
        server_frame = ttk.Frame(self.notebook)
        self.notebook.add(server_frame, text="Server Management")
        
        # Main content area
        content_frame = tk.Frame(server_frame)
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left side - Server list
        left_frame = tk.Frame(content_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Filter status label
        self.filter_status_label = tk.Label(left_frame, text="Showing: All Servers", 
                                           font=("Arial", 10), fg="blue")
        self.filter_status_label.pack(anchor="w", pady=(0, 5))
        
        # Server listbox with scrollbar
        listbox_frame = tk.Frame(left_frame)
        listbox_frame.pack(fill="both", expand=True)
        
        self.server_listbox = tk.Listbox(listbox_frame, font=("Arial", 9))
        scrollbar = tk.Scrollbar(listbox_frame, orient="vertical", command=self.server_listbox.yview)
        self.server_listbox.config(yscrollcommand=scrollbar.set)
        
        self.server_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Right side - Buttons
        right_frame = tk.Frame(content_frame)
        right_frame.pack(side="right", fill="y")
        
        # Server management buttons
        tk.Label(right_frame, text="Server Actions", font=("Arial", 11, "bold")).pack(pady=(0, 10))
        
        tk.Button(right_frame, text="Browse Servers", command=self.open_battlemetrics, 
                 bg="#4CAF50", fg="white", width=15).pack(pady=2)
        tk.Button(right_frame, text="Add Server", command=self.add_server, width=15).pack(pady=2)
        tk.Button(right_frame, text="Remove Server", command=self.remove_server, width=15).pack(pady=2)
        
        # Separator
        tk.Frame(right_frame, height=2, bg="gray").pack(fill="x", pady=10)
        
        # Filter buttons
        tk.Label(right_frame, text="Filter Servers", font=("Arial", 11, "bold")).pack(pady=(0, 10))
        
        tk.Button(right_frame, text="Show All", command=self.show_all_servers, width=15).pack(pady=2)
        tk.Button(right_frame, text="Hide Premium", command=self.hide_premium_servers, width=15).pack(pady=2)
        tk.Button(right_frame, text="Hide Non-Premium", command=self.hide_non_premium_servers, width=15).pack(pady=2)
        
        # Separator
        tk.Frame(right_frame, height=2, bg="gray").pack(fill="x", pady=10)
        
        # Danger zone
        tk.Label(right_frame, text="Danger Zone", font=("Arial", 11, "bold"), fg="red").pack(pady=(0, 10))
        
        tk.Button(right_frame, text="Delete All Premium", command=self.delete_all_premium, 
                 bg="#8B0000", fg="white", width=18).pack(pady=2)
        tk.Button(right_frame, text="Delete All Non-Premium", command=self.delete_all_non_premium, 
                 bg="#8B0000", fg="white", width=18).pack(pady=2)
    
    def create_basic_settings_tab(self):
        """Create the basic settings tab"""
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="Basic Settings")
        
        # Main content with two columns
        content_frame = tk.Frame(settings_frame)
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left column
        left_col = tk.Frame(content_frame)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # AFK Loop Interval
        interval_frame = tk.LabelFrame(left_col, text="AFK Loop Settings", padx=10, pady=10)
        interval_frame.pack(fill="x", pady=(0, 10))
        
        pause_frame = tk.Frame(interval_frame)
        pause_frame.pack(fill="x")
        
        self.pause_label = tk.Label(pause_frame, text="Interval:")
        self.pause_label.pack(side="left")
        self.pause_var = tk.StringVar(value="1 min")
        self.pause_dropdown = ttk.Combobox(pause_frame, textvariable=self.pause_var, 
                                          values=["1 min", "2 min", "5 min", "10 min", "15 min", "20 min", "25 min"], 
                                          width=12, state="readonly")
        self.pause_dropdown.pack(side="left", padx=10)
        
        # Connection Wait Time Setting
        connection_frame = tk.LabelFrame(left_col, text="Connection Settings", padx=10, pady=10)
        connection_frame.pack(fill="x", pady=(0, 10))
        
        connection_wait_frame = tk.Frame(connection_frame)
        connection_wait_frame.pack(fill="x")
        
        tk.Label(connection_wait_frame, text="Connection wait time:").pack(side="left")
        self.connection_wait_time_var = tk.StringVar(value=self.settings.get("connection_wait_time", "1 min"))
        self.connection_wait_time_dropdown = ttk.Combobox(connection_wait_frame, textvariable=self.connection_wait_time_var, 
                                                         values=["45 sec", "1 min", "1m 30s", "2 min"], 
                                                         width=8, state="readonly")
        self.connection_wait_time_dropdown.pack(side="left", padx=10)
        
        connection_note = tk.Label(connection_frame, text="Time to wait for server connection to stabilize", 
                                  font=("Arial", 8), wraplength=350)
        connection_note.pack(anchor="w", padx=20, pady=2)
        
        # Kill After Movement Setting
        kill_frame = tk.LabelFrame(left_col, text="Combat Settings", padx=10, pady=10)
        kill_frame.pack(fill="x", pady=(0, 10))
        
        self.kill_after_movement_var = tk.BooleanVar(value=self.settings["kill_after_movement"])
        self.kill_checkbox = tk.Checkbutton(kill_frame, text="Kill after movement (prevents spectating)", 
                                           variable=self.kill_after_movement_var, command=self.on_kill_after_movement_change)
        self.kill_checkbox.pack(anchor="w")
        
        kill_note = tk.Label(kill_frame, text="Note: Keep OFF so players can kill you for stats", 
                            font=("Arial", 8), wraplength=350)
        kill_note.pack(anchor="w", padx=20, pady=2)
        
        # Right column
        right_col = tk.Frame(content_frame)
        right_col.pack(side="right", fill="both", expand=True)
        
        # System Settings
        system_frame = tk.LabelFrame(right_col, text="System Settings", padx=10, pady=10)
        system_frame.pack(fill="x", pady=(0, 10))
        
        self.disable_disconnect_var = tk.BooleanVar(value=self.settings.get("disable_startup_disconnect", True))
        tk.Checkbutton(system_frame, text="Disable startup disconnect command", 
                      variable=self.disable_disconnect_var).pack(anchor="w", pady=2)
        
        self.disable_beep_var = tk.BooleanVar(value=self.settings.get("disable_beep", False))
        tk.Checkbutton(system_frame, text="Disable beep sounds", 
                      variable=self.disable_beep_var).pack(anchor="w", pady=2)
        
        # Special Modes
        modes_frame = tk.LabelFrame(right_col, text="Special Modes", padx=10, pady=10)
        modes_frame.pack(fill="x")
        
        self.minimal_activity_var = tk.BooleanVar(value=self.settings.get("minimal_activity", False))
        self.minimal_checkbox = tk.Checkbutton(modes_frame, text="Minimal Activity Mode", 
                                              variable=self.minimal_activity_var,
                                              command=self.on_minimal_activity_change)
        self.minimal_checkbox.pack(anchor="w", pady=2)
        
        minimal_note = tk.Label(modes_frame, text="Sets 25min interval + kill after movement", 
                               font=("Arial", 8), wraplength=350)
        minimal_note.pack(anchor="w", padx=20, pady=2)
    
    def create_automation_tab(self):
        """Create the automation settings tab"""
        auto_frame = ttk.Frame(self.notebook)
        self.notebook.add(auto_frame, text="Automation")
        
        # Main content with two columns
        content_frame = tk.Frame(auto_frame)
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left column
        left_col = tk.Frame(content_frame)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Game Management
        game_frame = tk.LabelFrame(left_col, text="Game Management", padx=10, pady=10)
        game_frame.pack(fill="x", pady=(0, 10))
        
        self.auto_start_rust_var = tk.BooleanVar(value=self.settings.get("auto_start_rust", False))
        tk.Checkbutton(game_frame, text="Auto start Rust and focus window", 
                      variable=self.auto_start_rust_var).pack(anchor="w", pady=2)
        
        # Rust load time setting
        load_time_frame = tk.Frame(game_frame)
        load_time_frame.pack(fill="x", pady=5)
        
        tk.Label(load_time_frame, text="Rust load time:").pack(side="left")
        self.rust_load_time_var = tk.StringVar(value=self.settings.get("rust_load_time", "1 min"))
        self.rust_load_time_dropdown = ttk.Combobox(load_time_frame, textvariable=self.rust_load_time_var, 
                                                   values=["30 sec", "1 min", "2 min", "3 min", "4 min", "5 min"], 
                                                   width=8, state="readonly")
        self.rust_load_time_dropdown.pack(side="left", padx=10)
        
        auto_start_note = tk.Label(game_frame, text="Starts via Steam, waits for load time, then focuses", 
                                  font=("Arial", 8), wraplength=350)
        auto_start_note.pack(anchor="w", padx=20, pady=2)
        
        # Auto Restart
        restart_frame = tk.LabelFrame(left_col, text="Auto Restart", padx=10, pady=10)
        restart_frame.pack(fill="x")
        
        self.auto_restart_game_var = tk.BooleanVar(value=self.settings.get("auto_restart_game", False))
        tk.Checkbutton(restart_frame, text="Auto restart game for updates", 
                      variable=self.auto_restart_game_var,
                      command=self.on_auto_restart_change).pack(anchor="w", pady=2)
        
        restart_interval_frame = tk.Frame(restart_frame)
        restart_interval_frame.pack(fill="x", pady=5)
        
        self.restart_label = tk.Label(restart_interval_frame, text="Restart every:")
        self.restart_label.pack(side="left")
        self.restart_interval_var = tk.StringVar(value=self.settings.get("restart_interval", "6h"))
        self.restart_dropdown = ttk.Combobox(restart_interval_frame, textvariable=self.restart_interval_var, 
                                           values=["1h", "2h", "3h", "6h", "8h", "12h", "24h"], width=8, state="readonly")
        self.restart_dropdown.pack(side="left", padx=10)
        
        # Right column
        right_col = tk.Frame(content_frame)
        right_col.pack(side="right", fill="both", expand=True)
        
        # Startup Settings
        startup_frame = tk.LabelFrame(right_col, text="Windows Startup", padx=10, pady=10)
        startup_frame.pack(fill="x")
        
        self.start_at_boot_var = tk.BooleanVar(value=self.settings.get("start_at_boot", False))
        tk.Checkbutton(startup_frame, text="Start farming at Windows startup", 
                      variable=self.start_at_boot_var).pack(anchor="w", pady=2)
        
        boot_note = tk.Label(startup_frame, text="Waits 2min after boot, then starts", 
                            font=("Arial", 8), wraplength=350)
        boot_note.pack(anchor="w", padx=20, pady=2)
    
    def create_server_switching_tab(self):
        """Create the server switching tab"""
        switch_frame = ttk.Frame(self.notebook)
        self.notebook.add(switch_frame, text="Server Switching")
        
        # Main content
        content_frame = tk.Frame(switch_frame)
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Enable/Disable
        enable_frame = tk.LabelFrame(content_frame, text="Auto Server Switching", padx=10, pady=10)
        enable_frame.pack(fill="x", pady=(0, 10))
        
        self.switch_enabled_var = tk.BooleanVar(value=self.settings["server_switching"]["enabled"])
        tk.Checkbutton(enable_frame, text="Enable Auto Server Switching", 
                      variable=self.switch_enabled_var).pack(anchor="w")
        
        # Two column layout for settings
        settings_container = tk.Frame(content_frame)
        settings_container.pack(fill="both", expand=True)
        
        # Left column - Timing settings
        left_col = tk.Frame(settings_container)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        timing_frame = tk.LabelFrame(left_col, text="Timing Settings", padx=10, pady=10)
        timing_frame.pack(fill="x", pady=(0, 10))
        
        time_range_frame = tk.Frame(timing_frame)
        time_range_frame.pack(fill="x")
        
        self.time_range_label = tk.Label(time_range_frame, text="Switch every:")
        self.time_range_label.pack(side="left")
        self.time_range_var = tk.StringVar(value=self.settings["server_switching"]["time_range"])
        self.time_range_combo = ttk.Combobox(time_range_frame, textvariable=self.time_range_var, 
                                            values=["1-2", "2-3", "3-6", "6-12"], width=10, state="readonly")
        self.time_range_combo.pack(side="left", padx=10)
        self.time_range_hours_label = tk.Label(time_range_frame, text="hours")
        self.time_range_hours_label.pack(side="left")
        
        # Stealth Mode
        stealth_frame = tk.LabelFrame(left_col, text="Stealth Mode", padx=10, pady=10)
        stealth_frame.pack(fill="x")
        
        self.stealth_mode_var = tk.BooleanVar(value=self.settings["server_switching"].get("stealth_mode", False))
        tk.Checkbutton(stealth_frame, text="Enable Stealth Mode", 
                      variable=self.stealth_mode_var,
                      command=self.on_stealth_mode_change).pack(anchor="w")
        
        stealth_note = tk.Label(stealth_frame, text="19min sessions, minimal activity, no respawn cycles", 
                               font=("Arial", 8), wraplength=350)
        stealth_note.pack(anchor="w", padx=20, pady=2)
        
        # Right column - Server selection
        right_col = tk.Frame(settings_container)
        right_col.pack(side="right", fill="both", expand=True)
        
        selection_frame = tk.LabelFrame(right_col, text="Server Selection", padx=10, pady=10)
        selection_frame.pack(fill="both", expand=True)
        
        tk.Button(selection_frame, text="Select Servers for Rotation", 
                 command=self.select_rotation_servers, width=25).pack(pady=10)
        
        # Status display for selected rotation servers
        self.rotation_status_label = tk.Label(selection_frame, text="", 
                                            font=("Arial", 9), fg="gray", wraplength=350, justify="left")
        self.rotation_status_label.pack(fill="both", expand=True, padx=10)
        self.update_rotation_status()
        
    def create_about_tab(self):
        """Create the about tab"""
        about_frame = ttk.Frame(self.notebook)
        self.notebook.add(about_frame, text="About")
        
        # Main content with padding
        content_frame = tk.Frame(about_frame)
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Purpose
        purpose_frame = tk.LabelFrame(content_frame, text="Purpose", padx=15, pady=15)
        purpose_frame.pack(fill="x", pady=(0, 20))
        
        purpose_text = tk.Label(purpose_frame, 
                               text="This tool automates AFK hour farming in Rust that appears on\nBattlemetrics server statistics.\n\n• Build legit looking profiles with accumulated playtime\n• Join higher tier groups that require lots of playtime hours\n• Automatically connects, respawns, and cycles between servers\n• Runs 24/7 with minimal user intervention\n• Supports server switching and stealth modes\n• Real hours that show up on your Battlemetrics profile", 
                               font=("Arial", 11), justify="left", wraplength=500)
        purpose_text.pack()
        
        # Links section
        links_frame = tk.LabelFrame(content_frame, text="Community & Support", padx=15, pady=15)
        links_frame.pack(fill="x")
        
        # GitHub link
        github_frame = tk.Frame(links_frame)
        github_frame.pack(pady=5)
        
        tk.Label(github_frame, text="GitHub:", font=("Arial", 11, "bold")).pack(side="left")
        github_link = tk.Label(github_frame, text="https://jlaiii.github.io/RUST-BM-AFK/", 
                              font=("Arial", 11), fg="blue", cursor="hand2")
        github_link.pack(side="left", padx=(10, 0))
        github_link.bind("<Button-1>", lambda e: self.open_github_link())
        
        # Discord link
        discord_frame = tk.Frame(links_frame)
        discord_frame.pack(pady=5)
        
        tk.Label(discord_frame, text="Discord:", font=("Arial", 11, "bold")).pack(side="left")
        discord_link = tk.Label(discord_frame, text="https://discord.gg/a5T2xBhKgt", 
                               font=("Arial", 11), fg="blue", cursor="hand2")
        discord_link.pack(side="left", padx=(10, 0))
        discord_link.bind("<Button-1>", lambda e: self.open_discord_link())
        
    def load_settings(self):
        settings_file = os.path.join(self.data_folder, "settings.json")
        try:
            if os.path.exists(settings_file):
                with open(settings_file, "r") as f:
                    saved_settings = json.load(f)
                    # Handle migration from old stealth_mode to kill_after_movement
                    if "stealth_mode" in saved_settings and "kill_after_movement" not in saved_settings:
                        saved_settings["kill_after_movement"] = saved_settings.pop("stealth_mode")

                    self.settings.update(saved_settings)
        except Exception as e:
            self.log_status(f"Error loading settings: {e}")
    
    def on_kill_after_movement_change(self):
        """Handle kill after movement checkbox change"""
        if self.kill_after_movement_var.get():
            # When kill after movement is enabled, set AFK loop to 10 minutes
            self.pause_var.set("10 min")
    
    def on_stealth_mode_change(self):
        """Handle stealth mode checkbox change"""
        if self.stealth_mode_var.get():
            # When stealth mode is enabled, disable time range dropdown
            self.time_range_combo.config(state="disabled")
            self.time_range_label.config(fg="gray")
            self.time_range_hours_label.config(fg="gray")
        else:
            # When stealth mode is disabled, enable time range dropdown
            self.time_range_combo.config(state="readonly")
            self.time_range_label.config(fg="black")
            self.time_range_hours_label.config(fg="black")
    
    def on_minimal_activity_change(self):
        """Handle minimal activity checkbox change"""
        if self.minimal_activity_var.get():
            # Store current values before changing them
            self.previous_pause_value = self.pause_var.get()
            self.previous_kill_value = self.kill_after_movement_var.get()
            
            # When minimal activity is enabled, set AFK loop to 25 minutes and enable kill after movement
            self.pause_var.set("25 min")
            self.kill_after_movement_var.set(True)
            
            # Gray out and disable the controls that are now automatic
            self.pause_dropdown.config(state="disabled")
            self.pause_label.config(fg="gray")
            self.kill_checkbox.config(state="disabled")
        else:
            # When minimal activity is disabled, restore previous values and re-enable the controls
            if hasattr(self, 'previous_pause_value'):
                self.pause_var.set(self.previous_pause_value)
            if hasattr(self, 'previous_kill_value'):
                self.kill_after_movement_var.set(self.previous_kill_value)
            
            self.pause_dropdown.config(state="readonly")
            self.pause_label.config(fg="black")
            self.kill_checkbox.config(state="normal")
    
    def on_auto_restart_change(self):
        """Handle auto restart checkbox change"""
        if self.auto_restart_game_var.get():
            # When auto restart is enabled, enable restart interval dropdown
            self.restart_dropdown.config(state="readonly")
            self.restart_label.config(fg="black")
        else:
            # When auto restart is disabled, disable restart interval dropdown
            self.restart_dropdown.config(state="disabled")
            self.restart_label.config(fg="gray")
    
    def save_settings(self):
        settings_file = os.path.join(self.data_folder, "settings.json")
        try:
            # Update settings from GUI
            self.settings["kill_after_movement"] = self.kill_after_movement_var.get()
            self.settings["disable_startup_disconnect"] = self.disable_disconnect_var.get()
            self.settings["disable_beep"] = self.disable_beep_var.get()
            self.settings["minimal_activity"] = self.minimal_activity_var.get()
            self.settings["auto_start_rust"] = self.auto_start_rust_var.get()
            self.settings["rust_load_time"] = self.rust_load_time_var.get()
            self.settings["connection_wait_time"] = self.connection_wait_time_var.get()
            self.settings["start_at_boot"] = self.start_at_boot_var.get()
            self.settings["auto_restart_game"] = self.auto_restart_game_var.get()
            self.settings["restart_interval"] = self.restart_interval_var.get()
            self.settings["server_switching"]["enabled"] = self.switch_enabled_var.get()
            self.settings["server_switching"]["time_range"] = self.time_range_var.get()
            self.settings["server_switching"]["stealth_mode"] = self.stealth_mode_var.get()
            # Note: selected_servers is updated directly in select_rotation_servers() method
            
            with open(settings_file, "w") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            self.log_status(f"Error saving settings: {e}")
    
    def reset_to_defaults(self):
        """Reset all settings to their default values"""
        # Show confirmation dialog
        if messagebox.askyesno("Reset Settings", 
                              "Are you sure you want to reset all settings to their default values?\n\n" +
                              "This will:\n" +
                              "• Reset AFK loop interval to 1 minute\n" +
                              "• Disable kill after movement\n" +
                              "• Enable initial startup disconnect command\n" +
                              "• Enable beep sounds\n" +
                              "• Disable auto server switching\n" +
                              "• Disable stealth mode\n" +
                              "• Clear server rotation selection\n\n" +
                              "This action cannot be undone!"):
            
            # Reset settings to defaults
            self.settings = {
                "pause_time": 60,  # 1 minute in seconds
                "kill_after_movement": False,
                "disable_startup_disconnect": True,
                "disable_beep": False,
                "minimal_activity": False,
                "auto_start_rust": False,
                "rust_load_time": "1 min",
                "connection_wait_time": "1 min",
                "start_at_boot": False,
                "auto_restart_game": False,
                "restart_interval": "6h",
                "server_switching": {
                    "enabled": False,
                    "time_range": "1-2",
                    "stealth_mode": False,
                    "selected_servers": []
                }
            }
            
            # Update GUI elements to reflect defaults
            self.pause_var.set("1 min")
            self.kill_after_movement_var.set(False)
            self.disable_disconnect_var.set(True)
            self.disable_beep_var.set(False)
            self.minimal_activity_var.set(False)
            self.auto_start_rust_var.set(False)
            self.rust_load_time_var.set("1 min")
            self.connection_wait_time_var.set("1 min")
            self.start_at_boot_var.set(False)
            self.auto_restart_game_var.set(False)
            self.restart_interval_var.set("6h")
            self.switch_enabled_var.set(False)
            self.time_range_var.set("1-2")
            self.stealth_mode_var.set(False)
            
            # Save the reset settings
            self.save_settings()
            
            # Update rotation status display
            self.update_rotation_status()
            
            # Update UI state based on reset stealth mode, minimal activity, and auto restart
            self.on_stealth_mode_change()
            self.on_minimal_activity_change()
            self.on_auto_restart_change()
            
            # Log the reset action
            self.log_status("Settings reset to default values")
            
            # Show success message
            messagebox.showinfo("Settings Reset", "All settings have been reset to their default values.")
    
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
    
    def update_rotation_status(self):
        """Update the rotation status display"""
        selected_servers = self.settings["server_switching"]["selected_servers"]
        if selected_servers:
            count = len(selected_servers)
            if count <= 3:
                # Show server names if 3 or fewer
                server_names = [self.servers[i]['name'] for i in selected_servers if i < len(self.servers)]
                status_text = f"Rotation servers ({count}): {', '.join(server_names)}"
            else:
                # Just show count if more than 3
                status_text = f"Rotation servers: {count} servers selected"
        else:
            status_text = "No servers selected for rotation"
        
        self.rotation_status_label.config(text=status_text)
    
    def select_rotation_servers(self):
        """Dialog to select which servers to include in rotation"""
        dialog = ServerRotationDialog(self.root, self.servers, 
                                     self.settings["server_switching"]["selected_servers"])
        
        # Wait for dialog to complete (modal behavior)
        self.root.wait_window(dialog.dialog)
        
        if dialog.result is not None:
            self.settings["server_switching"]["selected_servers"] = dialog.result
            self.save_settings()
            self.update_rotation_status()  # Update the status display
            
            # Show confirmation message with server names
            if dialog.result:
                server_names = [self.servers[i]['name'] for i in dialog.result]
                self.log_status(f"Updated server rotation list: {len(dialog.result)} servers selected")
                for i, server_idx in enumerate(dialog.result):
                    self.log_status(f"  {i+1}. {self.servers[server_idx]['name']}")
            else:
                self.log_status("Cleared server rotation list")
    
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
            elif pause_text == "15 min":
                pause_minutes = 15
            elif pause_text == "20 min":
                pause_minutes = 20
            elif pause_text == "25 min":
                pause_minutes = 25
            else:
                messagebox.showerror("Error", "Please select a valid AFK loop interval")
                return
            
            # If kill after movement is enabled, set AFK loop to 10 minutes
            if self.kill_after_movement_var.get():
                pause_minutes = 10
                self.pause_var.set("10 min")
                
            self.settings["pause_time"] = pause_minutes * 60
        except Exception:
            messagebox.showerror("Error", "Invalid AFK loop interval")
            return
        
        # Check server selection or rotation setup
        if self.switch_enabled_var.get():
            # Server switching is enabled - use rotation servers
            if not self.settings["server_switching"]["selected_servers"]:
                messagebox.showerror("Server Rotation Error", 
                                   "Auto Server Switching is enabled but no servers are selected for rotation.\n\n" +
                                   "Please:\n" +
                                   "1. Click 'Select Servers for Rotation' button\n" +
                                   "2. Choose which servers to rotate between\n" +
                                   "3. Click OK to save your selection\n\n" +
                                   "Or disable Auto Server Switching and select a single server from the list.")
                return
            # Validate all server indices are still valid
            invalid_indices = [i for i in self.settings["server_switching"]["selected_servers"] if i >= len(self.servers)]
            if invalid_indices:
                messagebox.showerror("Server Rotation Error", 
                                   "Some servers in your rotation list are no longer valid.\n\n" +
                                   "This can happen if servers were deleted after being added to rotation.\n\n" +
                                   "Please reselect servers for rotation.")
                return
            # Pick first server from rotation
            server_index = self.settings["server_switching"]["selected_servers"][0]
            self.selected_server = self.servers[server_index]
            self.setup_next_server_switch()
            self.log_status(f"Auto server switching enabled - starting with: {self.selected_server['name']}")
            self.log_status("AUTOMATION: Server selection complete, proceeding to automation setup...")
        else:
            # Server switching is disabled - use manual selection from listbox
            selection = self.server_listbox.curselection()
            if not selection:
                messagebox.showerror("Server Selection Error", 
                                   "No server selected.\n\n" +
                                   "Please:\n" +
                                   "1. Click on a server in the list to select it, OR\n" +
                                   "2. Enable Auto Server Switching and configure rotation servers")
                return
            # Get the actual server considering current filter
            displayed_servers = self.get_filtered_servers()
            if selection[0] < len(displayed_servers):
                self.selected_server = displayed_servers[selection[0]]
                self.log_status(f"Manual server selection: {self.selected_server['name']}")
            else:
                messagebox.showerror("Error", "Invalid server selection")
                return
        
        # Handle auto start Rust functionality
        auto_start_enabled = self.settings.get("auto_start_rust", False)
        self.log_status(f"AUTOMATION: Auto start Rust setting: {auto_start_enabled}")
        if auto_start_enabled:
            self.log_status("AUTOMATION: Checking if Rust is running...")
            rust_running = self.is_rust_running()
            self.log_status(f"AUTOMATION: Rust running status: {rust_running}")
            if not rust_running:
                # 5-second countdown before starting Rust
                for i in range(5, 0, -1):
                    self.status_label.config(text=f"Starting Rust in {i} seconds...")
                    self.root.update()
                    time.sleep(1)
                
                # Now start Rust
                self.status_label.config(text="Starting Rust via Steam...")
                self.root.update()
                
                self.log_status("AUTOMATION: Starting Rust via Steam...")
                if self.start_rust_via_steam():
                    
                    # Get load time from settings and convert to seconds
                    load_time_text = self.rust_load_time_var.get()
                    if load_time_text == "30 sec":
                        load_time_seconds = 30
                    elif load_time_text == "1 min":
                        load_time_seconds = 60
                    elif load_time_text == "2 min":
                        load_time_seconds = 120
                    elif load_time_text == "3 min":
                        load_time_seconds = 180
                    elif load_time_text == "4 min":
                        load_time_seconds = 240
                    elif load_time_text == "5 min":
                        load_time_seconds = 300
                    else:
                        load_time_seconds = 60  # Default to 1 minute
                    
                    # Update status during wait
                    self.status_label.config(text=f"Waiting {load_time_text} for Rust to load...")
                    self.root.update()
                    self.log_status(f"AUTOMATION: Waiting {load_time_text} for Rust to load...")
                    
                    # Wait for Rust to load
                    for i in range(load_time_seconds):
                        remaining = load_time_seconds - i
                        self.status_label.config(text=f"Waiting for Rust to load... ({remaining}s remaining)")
                        self.root.update()
                        time.sleep(1)
                    
                    # Focus the Rust window
                    self.status_label.config(text="Focusing Rust window...")
                    self.root.update()
                    if self.focus_rust_window():
                        self.log_status("AUTOMATION: Rust window focused successfully")
                        self.status_label.config(text="Rust window focused - Starting automation...")
                    else:
                        self.log_status("WARNING: Could not focus Rust window - continuing anyway")
                        self.status_label.config(text="Could not focus window - Starting automation anyway...")
                    self.root.update()
                    time.sleep(2)  # Give focus time to take effect
                else:
                    messagebox.showerror("Auto Start Failed", 
                                       "Failed to start Rust via Steam.\n\n" +
                                       "Please start Rust manually and try again.")
                    self.status_label.config(text="Failed to start Rust")
                    return
            else:
                self.log_status("AUTOMATION: Rust already running, focusing window...")
                self.status_label.config(text="Rust already running - Focusing window...")
                self.root.update()
                if self.focus_rust_window():
                    self.log_status("AUTOMATION: Rust window focused successfully")
                    self.status_label.config(text="Rust window focused - Starting automation...")
                else:
                    self.log_status("WARNING: Could not focus Rust window - continuing anyway")
                    self.status_label.config(text="Could not focus window - Starting automation anyway...")
                self.root.update()
                time.sleep(2)
            
            # Log that automation is continuing automatically
            self.log_status("AUTOMATION: Continuing automatically - no user interaction required")
            self.status_label.config(text="Automation starting...")
            self.root.update()
        else:
            # Show standard message for manual mode
            messagebox.showinfo("IMPORTANT", 
                               "You MUST tab into Rust after pressing OK!\n\n" +
                               "Press OK to continue and start the countdown.")
        
        # Log that we're proceeding to start the main loop
        self.log_status("AUTOMATION: Proceeding to start main AFK loop...")
        
        # Start countdown
        self.is_running = True
        self.start_time = datetime.now()
        self.current_server_start_time = datetime.now()
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        
        self.log_status("=== RUST HOUR ADDER INITIALIZATION ===")
        self.log_status(f"Session started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log_status(f"Target server: {self.selected_server['name']}")
        self.log_status(f"Server IP: {self.selected_server['ip']}")
        self.log_status(f"Premium server: {'Yes' if self.selected_server.get('premium', False) else 'No'}")
        self.log_status(f"Cycle interval: {pause_minutes} minutes ({pause_minutes * 60} seconds)")
        self.log_status(f"Kill after movement: {'ENABLED' if self.kill_after_movement_var.get() else 'DISABLED'}")
        self.log_status(f"Initial startup disconnect: {'DISABLED' if self.disable_disconnect_var.get() else 'ENABLED'}")
        
        if self.switch_enabled_var.get():
            rotation_count = len(self.settings["server_switching"]["selected_servers"])
            self.log_status(f"Auto server switching: ENABLED")
            self.log_status(f"   Servers in rotation: {rotation_count}")
            if self.settings["server_switching"]["stealth_mode"]:
                self.log_status(f"   Switch interval: 19 minutes (STEALTH MODE)")
            else:
                self.log_status(f"   Switch interval: {self.time_range_var.get()} hours")
        else:
            self.log_status(f"Auto server switching: DISABLED")
        
        self.log_status("="*60)
        
        self.afk_thread = threading.Thread(target=self.countdown_and_start, daemon=True)
        self.afk_thread.start()
        
        self.save_settings()
    
    def setup_next_server_switch(self):
        """Setup the next server switch time"""
        self.current_server_start_time = datetime.now()  # Track when this server session started
        
        if self.stealth_mode_var.get():
            # Stealth mode: Switch after 19 minutes
            self.next_server_switch_time = self.current_server_start_time + timedelta(minutes=19)
            
            self.log_status(f"NEXT SERVER SWITCH SCHEDULED (STEALTH MODE):")
            self.log_status(f"   Time: {self.next_server_switch_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.log_status(f"   Duration: 19 minutes from now")
            self.log_status(f"   Mode: Connect → Kill → Wait → Switch (minimal activity)")
        else:
            # Normal mode - use configured time range
            time_range = self.time_range_var.get()
            min_hours, max_hours = map(int, time_range.split('-'))
            switch_hours = random.uniform(min_hours, max_hours)
            self.next_server_switch_time = self.current_server_start_time + timedelta(hours=switch_hours)
            
            switch_hours_int = int(switch_hours)
            switch_minutes = int((switch_hours - switch_hours_int) * 60)
            
            self.log_status(f"NEXT SERVER SWITCH SCHEDULED:")
            self.log_status(f"   Time: {self.next_server_switch_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.log_status(f"   Duration: {switch_hours_int}h {switch_minutes}m from now")
            self.log_status(f"   Random interval: {min_hours}-{max_hours} hours (selected: {switch_hours:.1f}h)")
    
    def switch_to_next_server(self):
        """Switch to the next server in rotation"""
        if not self.settings["server_switching"]["selected_servers"]:
            self.log_status("WARNING: No servers configured for rotation")
            return
        
        switch_start = datetime.now()
        self.log_status("=== AUTO SERVER SWITCHING INITIATED ===")
        
        # Find current server index in rotation
        current_server_name = self.selected_server['name']
        rotation_servers = self.settings["server_switching"]["selected_servers"]
        
        self.log_status(f"Current server: {current_server_name}")
        self.log_status(f"Available servers in rotation: {len(rotation_servers)}")
        
        # Pick a random different server from rotation
        available_servers = [i for i in rotation_servers if self.servers[i]['name'] != current_server_name]
        if not available_servers:
            available_servers = rotation_servers  # If only one server, use it
            self.log_status("WARNING: Only one server in rotation, staying on same server")
        
        next_server_index = random.choice(available_servers)
        old_server = self.selected_server
        self.selected_server = self.servers[next_server_index]
        self.current_server_start_time = datetime.now()
        
        self.log_status(f"Switching FROM: {old_server['name']} ({old_server['ip']})")
        self.log_status(f"Switching TO: {self.selected_server['name']} ({self.selected_server['ip']})")
        
        # Disconnect from current server first
        self.log_status("SWITCH STEP 1: Disconnecting from current server")
        self.log_status("   Opening console (F1 key)")
        pyautogui.press('f1')
        time.sleep(1)
        
        self.log_status("   Typing command: 'client.disconnect'")
        self.human_type("client.disconnect")
        self.log_status("   Pressing Enter to execute disconnect")
        pyautogui.press('enter')
        time.sleep(1)
        
        self.log_status("   Closing console (F1 key)")
        pyautogui.press('f1')
        self.log_status("   Waiting 5 seconds for disconnect to complete...")
        time.sleep(5)  # Wait for disconnect to complete
        
        switch_duration = (datetime.now() - switch_start).total_seconds()
        self.log_status(f"SERVER SWITCH COMPLETED in {switch_duration:.1f}s")
        
        # Setup next switch
        self.setup_next_server_switch()
    
    def countdown_and_start(self):
        self.log_status("=== STARTING COUNTDOWN SEQUENCE ===")
        countdown_start = datetime.now()
        
        # Countdown from 10
        for i in range(10, 0, -1):
            if not self.is_running:
                self.log_status("Countdown interrupted by user")
                return
            
            self.status_label.config(text=f"Starting in {i}... Tab into game window!")
            
            if i <= 3:
                self.log_status(f"WARNING: FINAL COUNTDOWN: {i} seconds remaining - MAKE SURE RUST IS ACTIVE WINDOW!")
            else:
                self.log_status(f"Countdown: {i} seconds remaining - Please tab into Rust game window")
            
            time.sleep(1)
        
        if not self.is_running:
            self.log_status("Countdown cancelled by user")
            return
        
        countdown_end = datetime.now()
        countdown_duration = (countdown_end - countdown_start).total_seconds()
        
        # Beep to indicate start
        if not self.settings.get("disable_beep", False):
            try:
                winsound.Beep(1000, 500)
                self.log_status(f"START SIGNAL: Beep sound played (1000Hz, 500ms)")
            except Exception as e:
                self.log_status(f"WARNING: Could not play start beep: {e}")
        else:
            self.log_status("START SIGNAL: Beep sound disabled in settings")
        
        self.status_label.config(text="Hour Adder Running...")
        self.log_status(f"=== COUNTDOWN COMPLETED in {countdown_duration:.1f}s - RUST HOUR ADDER NOW ACTIVE ===")
        self.log_status(f"Target Server: {self.selected_server['name']} ({self.selected_server['ip']})")
        self.log_status(f"Cycle Interval: {self.settings['pause_time'] // 60} minutes")
        self.log_status(f"Kill After Movement: {'ENABLED' if self.settings['kill_after_movement'] else 'DISABLED'}")
        
        # Start the main AFK loop
        self.afk_loop()
    
    def afk_loop(self):
        """
        IMPORTANT: Disconnect/connect logic:
        - Disconnect: ONLY on first cycle (if "disable startup disconnect" is unchecked)
        - Connect: EVERY CYCLE (handles WiFi drops, network issues, server restarts)
        - Connection wait: EVERY CYCLE (ensures stable connection before respawn/movement)
        - Server switching: Handled separately with its own disconnect/connect logic
        
        NOTE: Connect command MUST happen every cycle because there's no way to detect
        if the player is actually connected to the server or not.
        """
        cycle_count = 0
        while self.is_running:
            try:
                cycle_count += 1
                self.log_status(f"=== Starting Hour Farming Cycle #{cycle_count} ===")
                
                # Check if we need to switch servers
                if self.switch_enabled_var.get() and self.next_server_switch_time:
                    current_time = datetime.now()
                    time_until_switch = (self.next_server_switch_time - current_time).total_seconds()
                    
                    if time_until_switch <= 0:
                        self.log_status("Server switch time reached - initiating switch")
                        self.switch_to_next_server()
                    else:
                        # Always show countdown with percentage at start of each cycle
                        hours_remaining = int(time_until_switch // 3600)
                        minutes_remaining = int((time_until_switch % 3600) // 60)
                        
                        # Calculate percentage progress and elapsed time
                        if self.current_server_start_time:
                            total_duration = (self.next_server_switch_time - self.current_server_start_time).total_seconds()
                            elapsed_duration = (current_time - self.current_server_start_time).total_seconds()
                            progress_percent = (elapsed_duration / total_duration) * 100
                            progress_percent = min(100, max(0, progress_percent))  # Clamp between 0-100
                            
                            # Format elapsed time
                            elapsed_hours = int(elapsed_duration // 3600)
                            elapsed_minutes = int((elapsed_duration % 3600) // 60)
                            elapsed_seconds = int(elapsed_duration % 60)
                            
                            if elapsed_hours > 0:
                                elapsed_str = f"{elapsed_hours}h {elapsed_minutes}m {elapsed_seconds}s"
                            elif elapsed_minutes > 0:
                                elapsed_str = f"{elapsed_minutes}m {elapsed_seconds}s"
                            else:
                                elapsed_str = f"{elapsed_seconds}s"
                            
                            self.log_status(f"Next server switch in: {hours_remaining}h {minutes_remaining}m ({progress_percent:.1f}% complete)")
                            self.log_status(f"Connected to current server for: {elapsed_str}")
                        else:
                            self.log_status(f"Next server switch in: {hours_remaining}h {minutes_remaining}m")
                elif self.switch_enabled_var.get():
                    self.log_status("WARNING: Server switching enabled but no switch time set")
                
                # Check if we're in stealth mode
                if (self.switch_enabled_var.get() and 
                    self.settings["server_switching"]["stealth_mode"]):
                    
                    # Stealth mode: Always run full cycle (Connect → Kill → Wait)
                    self.stealth_mode_cycle()
                    continue
                
                # Step 1: Disconnect from current server (ONLY on first cycle if not disabled)
                # The disconnect command should ONLY happen:
                # 1. First cycle (if "disable startup disconnect" is unchecked)
                # 2. When switching servers (handled separately in server switching logic)
                if cycle_count == 1 and not self.settings.get("disable_startup_disconnect", False):
                    step_start = datetime.now()
                    self.log_status("STEP 1: Disconnecting from current server")
                    self.log_status("   Opening console (F1 key)")
                    pyautogui.press('f1')
                    time.sleep(1)
                    
                    self.log_status("   Typing command: 'client.disconnect'")
                    self.human_type("client.disconnect")
                    self.log_status("   Pressing Enter to execute disconnect")
                    pyautogui.press('enter')
                    time.sleep(0.5)
                    
                    # Step 2: Close F1 after disconnect
                    self.log_status("   Closing console (F1 key)")
                    pyautogui.press('f1')
                    self.log_status("   Waiting 5 seconds for disconnect to complete...")
                    time.sleep(5)
                    
                    step_duration = (datetime.now() - step_start).total_seconds()
                    self.log_status(f"STEP 1 COMPLETED in {step_duration:.1f}s - Server disconnection finished")
                else:
                    if cycle_count == 1:
                        self.log_status("STEP 1 SKIPPED: Initial startup disconnect disabled in settings")
                    # No disconnect needed for subsequent cycles
                
                # Step 2: Connect to target server (EVERY CYCLE for reliability)
                # MUST happen every cycle to handle WiFi drops, network issues, server restarts, etc.
                # There's no way to detect if player is actually connected, so always reconnect
                step_start = datetime.now()
                self.log_status("STEP 2: Connecting to target server")
                self.log_status("   Opening console (F1 key)")
                pyautogui.press('f1')
                time.sleep(1)
                
                connect_command = f"client.connect {self.selected_server['ip']}"
                self.log_status(f"   Typing command: '{connect_command}'")
                self.log_status(f"   Target: {self.selected_server['name']}")
                self.human_type(connect_command)
                time.sleep(1)  # Wait after typing
                self.log_status("   Pressing Enter to execute connection")
                pyautogui.press('enter')
                time.sleep(1)  # Wait after pressing enter
                
                # Close F1
                self.log_status("   Closing console (F1 key)")
                pyautogui.press('f1')
                time.sleep(1)  # Wait after closing console
                
                step_duration = (datetime.now() - step_start).total_seconds()
                self.log_status(f"STEP 2 COMPLETED in {step_duration:.1f}s - Connection command sent")
                
                # Step 3: Wait for connection to stabilize (EVERY CYCLE for reliability)
                # Connection wait needed every cycle to ensure stable connection before respawn/movement
                # Get connection wait time from settings and convert to seconds
                wait_time_text = self.connection_wait_time_var.get()
                if wait_time_text == "45 sec":
                    wait_time_seconds = 45
                elif wait_time_text == "1 min":
                    wait_time_seconds = 60
                elif wait_time_text == "1m 30s":
                    wait_time_seconds = 90
                elif wait_time_text == "2 min":
                    wait_time_seconds = 120
                else:
                    wait_time_seconds = 60  # Default to 1 minute
                
                self.log_status(f"=== Starting {wait_time_text} connection stabilization wait ===")
                connection_wait_start = datetime.now()
                
                for second in range(wait_time_seconds):
                    if not self.is_running:
                        self.log_status("AFK loop stopped by user during connection wait")
                        return
                    
                    # Log every 15 seconds during this wait with detailed progress
                    if second > 0 and second % 15 == 0:
                        remaining_seconds = wait_time_seconds - second
                        elapsed_seconds = second
                        progress_percent = (second / wait_time_seconds) * 100
                        
                        self.log_status(f"Connection wait progress: {elapsed_seconds}s elapsed | "
                                      f"{remaining_seconds}s remaining | "
                                      f"{progress_percent:.1f}% complete")
                    
                    # Update status every 5 seconds
                    if second % 5 == 0:
                        remaining = wait_time_seconds - second
                        self.status_label.config(text=f"Connecting... {remaining}s remaining")
                    
                    time.sleep(1)
                
                connection_wait_end = datetime.now()
                connection_wait_duration = (connection_wait_end - connection_wait_start).total_seconds()
                self.log_status(f"=== Connection wait completed in {connection_wait_duration:.1f} seconds ===")
                
                # Step 6: Open F1 and type respawn
                step_start = datetime.now()
                self.log_status("STEP 3: Respawning player")
                self.log_status("   Opening console (F1 key)")
                pyautogui.press('f1')
                time.sleep(1)
                
                self.log_status("   Typing command: 'respawn'")
                self.human_type("respawn")
                time.sleep(1)  # Wait after typing
                self.log_status("   Pressing Enter to execute respawn")
                pyautogui.press('enter')
                time.sleep(1)  # Wait after pressing enter
                
                # Step 7: Close F1
                self.log_status("   Closing console (F1 key)")
                pyautogui.press('f1')
                time.sleep(1)  # Wait after closing console
                
                step_duration = (datetime.now() - step_start).total_seconds()
                self.log_status(f"STEP 3 COMPLETED in {step_duration:.1f}s - Respawn command executed")
                
                # Step 8: Wait 5 seconds
                self.log_status("STEP 4: Post-respawn stabilization")
                self.log_status("   Waiting 5 seconds for respawn to complete...")
                for i in range(5):
                    if not self.is_running:
                        return
                    self.status_label.config(text=f"Respawn wait: {5-i}s remaining")
                    time.sleep(1)
                self.log_status("STEP 4 COMPLETED - Respawn stabilization finished")
                
                # Step 9: Press spacebar and W
                step_start = datetime.now()
                self.log_status("STEP 5: Performing movement actions")
                self.log_status("   Pressing spacebar (waking player from sleep)")
                pyautogui.press('space')
                time.sleep(2)
                
                self.log_status("   Pressing and holding W key for movement...")
                pyautogui.keyDown('w')
                self.log_status("   Holding W key for 1 second...")
                time.sleep(1)
                pyautogui.keyUp('w')
                self.log_status("   Released W key")
                
                step_duration = (datetime.now() - step_start).total_seconds()
                self.log_status(f"STEP 5 COMPLETED in {step_duration:.1f}s - Movement actions finished")
                
                # Kill After Movement: Kill player to prevent spectating
                if self.settings["kill_after_movement"]:
                    step_start = datetime.now()
                    self.log_status("KILL AFTER MOVEMENT ACTIVATED - Eliminating player to prevent spectating")
                    self.log_status("   Opening console (F1 key)")
                    pyautogui.press('f1')
                    time.sleep(1)
                    
                    self.log_status("   Typing command: 'kill'")
                    self.human_type("kill")
                    self.log_status("   Pressing Enter to execute kill command")
                    pyautogui.press('enter')
                    time.sleep(0.5)
                    
                    self.log_status("   Closing console (F1 key)")
                    pyautogui.press('f1')
                    
                    step_duration = (datetime.now() - step_start).total_seconds()
                    self.log_status(f"KILL AFTER MOVEMENT COMPLETED in {step_duration:.1f}s - Player eliminated successfully")
                else:
                    self.log_status("INFO: Kill after movement disabled - Player remains alive")
                
                # Wait for the specified pause time before next cycle
                pause_time = self.settings["pause_time"]
                self.log_status(f"=== Starting pause period: {pause_time // 60} minutes {pause_time % 60} seconds ===")
                
                for second in range(pause_time):
                    if not self.is_running:
                        self.log_status("AFK loop stopped by user during pause period")
                        return
                    
                    # Log every 30 seconds during pause with detailed progress
                    if second > 0 and second % 30 == 0:
                        remaining_minutes = (pause_time - second) // 60
                        remaining_seconds = (pause_time - second) % 60
                        elapsed_minutes = second // 60
                        elapsed_seconds = second % 60
                        progress_percent = (second / pause_time) * 100
                        
                        self.log_status(f"Pause progress: {elapsed_minutes}m {elapsed_seconds}s elapsed | "
                                      f"{remaining_minutes}m {remaining_seconds}s remaining | "
                                      f"{progress_percent:.1f}% complete")
                    
                    # Update status label with countdown
                    if second % 5 == 0:  # Update every 5 seconds to avoid spam
                        remaining_total = pause_time - second
                        remaining_minutes = remaining_total // 60
                        remaining_seconds = remaining_total % 60
                        self.status_label.config(text=f"Next cycle in: {remaining_minutes}m {remaining_seconds}s")
                    
                    time.sleep(1)
                
                self.log_status(f"=== Pause period completed. Cycle #{cycle_count} finished ===")
                
                # Log cycle completion stats
                if cycle_count % 5 == 0:  # Every 5 cycles, show summary
                    total_elapsed = datetime.now() - self.start_time
                    hours, remainder = divmod(total_elapsed.total_seconds(), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    self.log_status(f"*** MILESTONE: Completed {cycle_count} cycles in {int(hours)}h {int(minutes)}m {int(seconds)}s ***")
                    
                    time.sleep(1)
                    
            except Exception as e:
                error_msg = f"Error in hour farming loop: {e}"
                self.log_status(error_msg)
                time.sleep(1)
    
    def stealth_mode_cycle(self):
        """Execute a stealth mode cycle: Connect → Kill → Wait"""
        self.log_status("=== STEALTH MODE CYCLE ===")
        
        # Step 1: Disconnect from current server first (if not disabled)
        if not self.settings.get("disable_startup_disconnect", False):
            step_start = datetime.now()
            self.log_status("STEALTH STEP 1: Disconnecting from current server")
            self.log_status("   Opening console (F1 key)")
            pyautogui.press('f1')
            time.sleep(1)
            
            self.log_status("   Typing command: 'client.disconnect'")
            self.human_type("client.disconnect")
            self.log_status("   Pressing Enter to execute disconnect")
            pyautogui.press('enter')
            time.sleep(0.5)
            
            self.log_status("   Closing console (F1 key)")
            pyautogui.press('f1')
            self.log_status("   Waiting 5 seconds for disconnect to complete...")
            time.sleep(5)
            
            step_duration = (datetime.now() - step_start).total_seconds()
            self.log_status(f"STEALTH STEP 1 COMPLETED in {step_duration:.1f}s - Server disconnection finished")
        else:
            self.log_status("STEALTH STEP 1 SKIPPED: Initial startup disconnect disabled in settings")
            time.sleep(1)
        
        # Step 2: Connect to target server
        step_start = datetime.now()
        self.log_status("STEALTH STEP 2: Connecting to target server")
        self.log_status("   Opening console (F1 key)")
        pyautogui.press('f1')
        time.sleep(1)  # Wait after opening console
        
        connect_command = f"client.connect {self.selected_server['ip']}"
        self.log_status(f"   Typing command: '{connect_command}'")
        self.log_status(f"   Target: {self.selected_server['name']}")
        self.human_type(connect_command)
        time.sleep(1)  # Wait after typing
        self.log_status("   Pressing Enter to execute connection")
        pyautogui.press('enter')
        time.sleep(1)  # Wait after pressing enter
        
        self.log_status("   Closing console (F1 key)")
        pyautogui.press('f1')
        time.sleep(1)  # Wait after closing console
        
        step_duration = (datetime.now() - step_start).total_seconds()
        self.log_status(f"STEALTH STEP 2 COMPLETED in {step_duration:.1f}s - Connection command sent")
        
        # Step 3: Wait for connection to stabilize
        # Get connection wait time from settings and convert to seconds
        wait_time_text = self.connection_wait_time_var.get()
        if wait_time_text == "45 sec":
            wait_time_seconds = 45
        elif wait_time_text == "1 min":
            wait_time_seconds = 60
        elif wait_time_text == "1m 30s":
            wait_time_seconds = 90
        elif wait_time_text == "2 min":
            wait_time_seconds = 120
        else:
            wait_time_seconds = 60  # Default to 1 minute
        
        self.log_status(f"STEALTH STEP 3: Connection stabilization wait ({wait_time_text})")
        for second in range(wait_time_seconds):
            if not self.is_running:
                return
            if second % 10 == 0 and second > 0:
                remaining = wait_time_seconds - second
                self.log_status(f"   Connection wait: {remaining}s remaining")
            time.sleep(1)
        
        self.log_status("STEALTH STEP 3 COMPLETED - Connection stabilized")
        
        # Step 4: Kill player immediately (stealth mode)
        step_start = datetime.now()
        self.log_status("STEALTH STEP 4: Eliminating player for stealth mode")
        self.log_status("   Opening console (F1 key)")
        pyautogui.press('f1')
        time.sleep(1)  # Wait after opening console
        
        self.log_status("   Typing command: 'kill'")
        self.human_type("kill")
        time.sleep(1)  # Wait after typing
        self.log_status("   Pressing Enter to execute kill command")
        pyautogui.press('enter')
        time.sleep(1)  # Wait after pressing enter
        
        self.log_status("   Closing console (F1 key)")
        pyautogui.press('f1')
        time.sleep(1)  # Wait after closing console
        
        step_duration = (datetime.now() - step_start).total_seconds()
        self.log_status(f"STEALTH STEP 4 COMPLETED in {step_duration:.1f}s - Player eliminated for stealth mode")
        
        self.log_status("=== STEALTH MODE: Now waiting for server switch time (19 minutes) ===")
        self.log_status("   Player is dead - minimal server activity - accumulating hours silently")
    
    def is_rust_running(self):
        """Check if RustClient.exe is running"""
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and 'RustClient.exe' in proc.info['name']:
                    return True
            return False
        except ImportError:
            self.log_status("ERROR: psutil package not installed - installing now...")
            if install_package("psutil==5.9.0"):
                self.log_status("SUCCESS: psutil installed, retrying Rust detection...")
                return self.is_rust_running()  # Retry after installation
            else:
                self.log_status("ERROR: Failed to install psutil - assuming Rust is not running")
                return False
        except Exception as e:
            self.log_status(f"Error checking if Rust is running: {e}")
            return False
    
    def start_rust_via_steam(self):
        """Start Rust via Steam"""
        try:
            self.log_status("AUTOMATION: Starting Rust via Steam...")
            # Rust's Steam App ID is 252490
            steam_command = "steam://run/252490"
            subprocess.Popen(f'start "" "{steam_command}"', shell=True)
            self.log_status("AUTOMATION: Steam launch command sent")
            return True
        except Exception as e:
            self.log_status(f"ERROR: Failed to start Rust via Steam: {e}")
            return False
    
    def focus_rust_window(self):
        """Focus the Rust game window"""
        try:
            import pygetwindow as gw
            rust_windows = gw.getWindowsWithTitle("Rust")
            if rust_windows:
                rust_window = rust_windows[0]
                rust_window.activate()
                self.log_status("AUTOMATION: Rust window focused successfully")
                return True
            else:
                self.log_status("WARNING: Rust window not found - make sure Rust is running")
                # Try alternative window titles
                alt_titles = ["RustClient", "Rust Client"]
                for title in alt_titles:
                    alt_windows = gw.getWindowsWithTitle(title)
                    if alt_windows:
                        alt_windows[0].activate()
                        self.log_status(f"AUTOMATION: Found and focused window with title: {title}")
                        return True
                return False
        except ImportError:
            self.log_status("ERROR: pygetwindow package not installed - installing now...")
            if install_package("pygetwindow==0.0.9"):
                self.log_status("SUCCESS: pygetwindow installed, retrying window focus...")
                return self.focus_rust_window()  # Retry after installation
            else:
                self.log_status("ERROR: Failed to install pygetwindow - window focusing disabled")
                return False
        except Exception as e:
            self.log_status(f"ERROR: Failed to focus Rust window: {e}")
            return False
    
    def kill_rust_process(self):
        """Kill the Rust process"""
        try:
            import psutil
            killed = False
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and 'RustClient.exe' in proc.info['name']:
                    proc.terminate()
                    killed = True
                    self.log_status(f"AUTOMATION: Killed Rust process (PID: {proc.info['pid']})")
            return killed
        except ImportError:
            self.log_status("ERROR: psutil package not installed - installing now...")
            if install_package("psutil==5.9.0"):
                self.log_status("SUCCESS: psutil installed, retrying process kill...")
                return self.kill_rust_process()  # Retry after installation
            else:
                self.log_status("ERROR: Failed to install psutil - process management disabled")
                return False
        except Exception as e:
            self.log_status(f"ERROR: Failed to kill Rust process: {e}")
            return False
    
    def human_type(self, text):
        """Type text with human-like timing"""
        typing_start = datetime.now()
        char_count = len(text)
        
        for i, char in enumerate(text):
            if not self.is_running:
                self.log_status(f"WARNING: Typing interrupted at character {i+1}/{char_count}")
                return
            
            pyautogui.write(char)
            # Random delay between 0.05 and 0.15 seconds for human-like typing
            delay = 0.05 + (time.time() % 0.1)
            time.sleep(delay)
        
        typing_duration = (datetime.now() - typing_start).total_seconds()
        avg_char_time = typing_duration / char_count if char_count > 0 else 0
        self.log_status(f"   Typed '{text}' ({char_count} chars in {typing_duration:.2f}s, avg: {avg_char_time:.3f}s/char)")
    
    def stop_afk(self, play_beep=True):
        stop_time = datetime.now()
        self.is_running = False
        
        # Calculate session statistics
        if self.start_time:
            total_session_time = stop_time - self.start_time
            hours, remainder = divmod(total_session_time.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            self.log_status("=== RUST HOUR ADDER STOPPED BY USER ===")
            self.log_status(f"SESSION STATISTICS:")
            self.log_status(f"   Start time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.log_status(f"   Stop time: {stop_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.log_status(f"   Total runtime: {int(hours)}h {int(minutes)}m {int(seconds)}s")
            self.log_status(f"   Server: {self.selected_server['name'] if self.selected_server else 'None'}")
            self.log_status(f"   Battlemetrics hours added: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}")
        else:
            self.log_status("Rust Hour Adder stopped by user (no session data)")
        
        if self.afk_thread and self.afk_thread.is_alive():
            self.log_status("Waiting for AFK thread to terminate...")
            self.afk_thread.join(timeout=2)
            if self.afk_thread.is_alive():
                self.log_status("WARNING: AFK thread did not terminate cleanly")
            else:
                self.log_status("AFK thread terminated successfully")
        
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.status_label.config(text="Stopped")
        
        # Play stop sound (only if requested and not disabled)
        if play_beep and not self.settings.get("disable_beep", False):
            try:
                winsound.Beep(500, 300)
                self.log_status("Stop signal: Beep sound played (500Hz, 300ms)")
            except Exception as e:
                self.log_status(f"WARNING: Could not play stop beep: {e}")
        elif not play_beep:
            self.log_status("Stop signal: Beep sound skipped (program closing)")
        else:
            self.log_status("Stop signal: Beep sound disabled in settings")
        
        self.log_status("=== SESSION ENDED ===")
        self.log_status("="*60)
    
    def open_github_link(self):
        """Open the GitHub link in the default web browser"""
        import webbrowser
        webbrowser.open("https://jlaiii.github.io/RUST-BM-AFK/")
        self.log_status("Opened GitHub link in browser")
    
    def open_discord_link(self):
        """Open the Discord invite link in the default web browser"""
        import webbrowser
        webbrowser.open("https://discord.gg/a5T2xBhKgt")
        self.log_status("Opened Discord invite in browser")
    
    def open_battlemetrics(self):
        """Open Battlemetrics Rust servers page in the default web browser"""
        import webbrowser
        webbrowser.open("https://www.battlemetrics.com/servers/rust")
        self.log_status("Opened Battlemetrics server browser in browser")
    
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
        self.stop_afk(play_beep=False)  # Don't play beep when closing program
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
            # Allow clearing selection but warn user
            if messagebox.askyesno("Clear Selection", 
                                  "No servers selected. This will clear the rotation list.\n\n" +
                                  "Are you sure you want to continue?"):
                self.result = []
                self.dialog.destroy()
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