import subprocess
import sys
import os
import socket
import concurrent.futures

def install_package(package):
    """Install a package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing package {package}: {e}")
        return False

def check_and_install_dependencies():
    """Check and install required packages"""
    required_packages = {
        'keyboard': 'keyboard==0.13.5',
        'pyautogui': 'pyautogui==0.9.54',
        'pygetwindow': 'pygetwindow==0.0.9',
        'psutil': 'psutil==5.9.0',
        'requests': 'requests'
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
import requests
import re
import webbrowser

# Disable pyautogui failsafe to prevent accidental mouse movement from stopping the program
pyautogui.FAILSAFE = False

class RustAFKHourAdder:
    def __init__(self):
        # Version information
        self.current_version = "1.0.0"
        self.github_repo = "jlaiii/BattleMetrics-Rust-Analytics"
        self.version_url = f"https://raw.githubusercontent.com/{self.github_repo}/main/version.json"
        self.script_url = f"https://raw.githubusercontent.com/{self.github_repo}/main/rust_battlemetrics_hour_adder.py"
        
        self.root = tk.Tk()
        self.root.title(f"RUST BM AFK Tool v{self.current_version} - Hour Farming Made Easy")
        self.root.geometry("900x730")  # Slightly taller to show all content
        self.root.resizable(True, True)  # Allow resizing so users can adjust if needed
        self.root.minsize(600, 400)  # Set minimum window size for usability
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create data folder
        self.data_folder = "data"
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
        
        # Default settings
        self.settings = {
            "pause_time": 60,  # 1 minute in seconds
            "kill_after_movement": False,  # Kill player after movement to prevent spectating
            "enable_startup_disconnect": False,  # Option to enable initial disconnect command when starting
            "disable_beep": True,  # Option to disable beep sounds
            "auto_check_updates": True,  # Option to automatically check for updates on startup
            "auto_update": False,  # Option to automatically download and install updates
            "minimal_activity": False,  # Option to enable minimal activity mode (19min + kill after movement)
            "auto_start_rust": True,  # Option to auto start Rust via Steam
            "rust_load_time": "1 min",  # How long to wait for Rust to load
            "connection_wait_time": "1 min",  # How long to wait for connection to stabilize
            "start_at_boot": False,  # Option to start farming at Windows startup
            "boot_wait_time": "4 min",  # How long to wait after Windows boot before starting
            "auto_restart_game": False,  # Option to auto restart game for updates
            "restart_interval": "3h",  # How often to restart the game
            "typing_mode": "human",  # "human" for realistic typing, "bot" for instant paste, "kid" for slow with mistakes, "pro" for fast ~90 WPM
            "add_servers_auto_start": True,  # Auto-start Rust for Server History Builder
            "add_servers_time": "1 min",  # Time per server for Server History Builder
            "add_servers_type": "all",  # Server type selection for Server History Builder
            "selected_server_index": 0,  # Index of selected server in the list
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
        self.initial_disconnect_done = False  # Track if we've done the initial disconnect
        
        # Server adding variables
        self.is_adding_servers = False
        self.add_servers_thread = None
        self.current_add_servers_list = []
        self.current_add_server_index = 0
        
        # Initialize log file path - use consistent filename
        self.log_file = os.path.join(self.data_folder, "afk_log.txt")
        
        # Load servers from separate file
        self.servers = self.load_servers()
        
        # Server filtering state
        self.server_filter = "all"  # "all", "premium", "non_premium"
        
        self.load_settings()
        self.create_gui()
        
        # Check for updates in background if enabled
        if self.settings.get("auto_check_updates", True):
            self.root.after(2000, self.background_update_check)  # Check after 2 seconds
        
        # Check if we should start farming at boot
        if self.settings.get("start_at_boot", False):
            self.root.after(1000, self.handle_startup_farming)  # Check after 1 second
    
    def create_menu_bar(self):
        """Create the application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Check for Updates", command=self.check_for_updates)
        help_menu.add_command(label="View Changelog", command=self.show_changelog)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about)
    
    def background_update_check(self):
        """Check for updates in background without blocking UI"""
        def check_updates():
            try:
                # Add cache-busting parameter to force fresh data from GitHub
                import time
                cache_buster = int(time.time())
                url_with_cache_buster = f"{self.version_url}?t={cache_buster}"
                self.log_status(f"Checking for updates from: {url_with_cache_buster}")
                response = requests.get(url_with_cache_buster, timeout=10)
                if response.status_code == 200:
                    remote_data = response.json()
                    remote_version = remote_data.get("version", "0.0.0")
                    
                    self.log_status(f"Current version: {self.current_version}, Remote version: {remote_version}")
                    
                    if self.is_newer_version(remote_version, self.current_version):
                        self.log_status("Update available! Showing notification...")
                        # Schedule UI update on main thread
                        self.root.after(0, lambda: self.show_update_notification(remote_data))
                    else:
                        self.log_status("No updates available")
                else:
                    self.log_status(f"Update check failed: HTTP {response.status_code}")
            except Exception as e:
                self.log_status(f"Background update check failed: {e}")
        
        # Run in background thread
        threading.Thread(target=check_updates, daemon=True).start()
    
    def check_for_updates(self):
        """Manual update check with user feedback"""
        try:
            # Add cache-busting parameter to force fresh data from GitHub
            import time
            cache_buster = int(time.time())
            url_with_cache_buster = f"{self.version_url}?t={cache_buster}"
            self.log_status(f"Checking for updates from: {url_with_cache_buster}")
            response = requests.get(url_with_cache_buster, timeout=10)
            
            if response.status_code == 200:
                remote_data = response.json()
                remote_version = remote_data.get("version", "0.0.0")
                
                if self.is_newer_version(remote_version, self.current_version):
                    self.show_update_notification(remote_data)
                else:
                    messagebox.showinfo("No Updates", f"You're running the latest version ({self.current_version})")
            else:
                messagebox.showerror("Update Check Failed", f"Failed to check for updates: HTTP {response.status_code}")
                
        except Exception as e:
            messagebox.showerror("Update Check Failed", f"Failed to check for updates: {e}")
    
    def is_newer_version(self, remote_version, current_version):
        """Compare version strings (semantic versioning)"""
        try:
            def version_tuple(v):
                return tuple(map(int, v.split('.')))
            return version_tuple(remote_version) > version_tuple(current_version)
        except:
            return False
    
    def show_update_notification(self, remote_data):
        """Show update notification dialog with options"""
        remote_version = remote_data.get("version", "Unknown")
        changelog = remote_data.get("changelog", [])
        
        # Check if auto-update is enabled
        if self.settings.get("auto_update", False):
            self.log_status(f"Auto-update enabled, installing version {remote_version} automatically...")
            self.start_update_process(None, remote_data)
            return
        
        # Create update notification window
        update_window = tk.Toplevel(self.root)
        update_window.title("Update Available")
        update_window.geometry("500x400")
        update_window.resizable(False, False)
        update_window.transient(self.root)
        update_window.grab_set()
        
        # Center the window
        update_window.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
        
        # Header
        header_frame = tk.Frame(update_window, bg="#2c3e50")
        header_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(header_frame, text="Update Available!", 
                font=("Arial", 16, "bold"), fg="white", bg="#2c3e50").pack(pady=10)
        
        # Version info
        info_frame = tk.Frame(update_window)
        info_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(info_frame, text=f"Current Version: {self.current_version}", 
                font=("Arial", 11)).pack(anchor="w")
        tk.Label(info_frame, text=f"New Version: {remote_version}", 
                font=("Arial", 11, "bold"), fg="#27ae60").pack(anchor="w")
        
        # Changelog
        changelog_frame = tk.LabelFrame(update_window, text="What's New", padx=10, pady=5)
        changelog_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        changelog_text = tk.Text(changelog_frame, height=8, wrap="word", font=("Arial", 10))
        scrollbar = tk.Scrollbar(changelog_frame, command=changelog_text.yview)
        changelog_text.config(yscrollcommand=scrollbar.set)
        
        changelog_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Add changelog content
        if changelog:
            for item in changelog:
                changelog_text.insert("end", f"• {item}\n")
        else:
            changelog_text.insert("end", "No changelog available for this version.")
        
        changelog_text.config(state="disabled")
        
        # Buttons
        button_frame = tk.Frame(update_window)
        button_frame.pack(fill="x", padx=20, pady=20)
        
        # Update button
        update_btn = tk.Button(button_frame, text="Update Now", 
                              bg="#27ae60", fg="white", font=("Arial", 11, "bold"),
                              command=lambda: self.start_update_process(update_window, remote_data))
        update_btn.pack(side="left", padx=(0, 10))
        
        # View on GitHub button
        github_btn = tk.Button(button_frame, text="View on GitHub", 
                              bg="#3498db", fg="white", font=("Arial", 11),
                              command=lambda: webbrowser.open(remote_data.get("github_url", f"https://github.com/{self.github_repo}")))
        github_btn.pack(side="left", padx=(0, 10))
        
        # Later button
        later_btn = tk.Button(button_frame, text="Maybe Later", 
                             bg="#95a5a6", fg="white", font=("Arial", 11),
                             command=update_window.destroy)
        later_btn.pack(side="right")
    
    def start_update_process(self, parent_window, remote_data):
        """Start the update process with progress dialog"""
        if parent_window:
            parent_window.destroy()
        
        # Create progress window
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Updating...")
        progress_window.geometry("400x200")
        progress_window.resizable(False, False)
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        # Center the window
        progress_window.geometry("+%d+%d" % (self.root.winfo_rootx() + 100, self.root.winfo_rooty() + 100))
        
        # Progress content
        tk.Label(progress_window, text="Updating RUST BM AFK Tool...", 
                font=("Arial", 14, "bold")).pack(pady=20)
        
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_window, variable=progress_var, maximum=100)
        progress_bar.pack(fill="x", padx=40, pady=10)
        
        status_label = tk.Label(progress_window, text="Preparing update...", font=("Arial", 10))
        status_label.pack(pady=10)
        
        def update_progress(value, text):
            progress_var.set(value)
            status_label.config(text=text)
            progress_window.update()
        
        def perform_update():
            try:
                # Step 1: Download new version
                update_progress(20, "Downloading new version...")
                response = requests.get(self.script_url, timeout=30)
                
                if response.status_code != 200:
                    raise Exception(f"Download failed: HTTP {response.status_code}")
                
                update_progress(50, "Preparing installation...")
                
                # Step 2: Create backup
                script_path = os.path.abspath(__file__)
                backup_path = script_path + ".backup"
                
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                
                import shutil
                shutil.copy2(script_path, backup_path)
                
                update_progress(70, "Installing update...")
                
                # Step 3: Write new version
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                update_progress(90, "Finalizing...")
                
                # Step 4: Update version file
                new_version_data = {
                    "version": remote_data.get("version", "1.0.0"),
                    "release_date": remote_data.get("release_date", datetime.now().strftime("%Y-%m-%d")),
                    "download_url": remote_data.get("download_url", ""),
                    "github_url": remote_data.get("github_url", f"https://github.com/{self.github_repo}"),
                    "changelog": remote_data.get("changelog", []),
                    "version_history": remote_data.get("version_history", [])
                }
                
                version_file = "version.json"
                with open(version_file, 'w') as f:
                    json.dump(new_version_data, f, indent=2)
                
                update_progress(100, "Update complete!")
                
                # Step 5: Show countdown and restart
                time.sleep(1)
                progress_window.destroy()
                
                # Show countdown dialog
                self.show_restart_countdown(remote_data.get('version', 'Unknown'))
                
            except Exception as e:
                progress_window.destroy()
                messagebox.showerror("Update Failed", f"Failed to update: {e}\n\nPlease try again or download manually from GitHub.")
        
        # Start update in background
        threading.Thread(target=perform_update, daemon=True).start()
    
    def show_restart_countdown(self, new_version):
        """Show countdown dialog before restarting"""
        # Create countdown window
        countdown_window = tk.Toplevel(self.root)
        countdown_window.title("Update Complete")
        countdown_window.geometry("400x250")
        countdown_window.resizable(False, False)
        countdown_window.transient(self.root)
        countdown_window.grab_set()
        
        # Center the window
        countdown_window.geometry("+%d+%d" % (self.root.winfo_rootx() + 100, self.root.winfo_rooty() + 100))
        
        # Header
        header_frame = tk.Frame(countdown_window, bg="#27ae60")
        header_frame.pack(fill="x", pady=(0, 20))
        
        tk.Label(header_frame, text="Update Complete!", 
                font=("Arial", 16, "bold"), fg="white", bg="#27ae60").pack(pady=15)
        
        # Content
        content_frame = tk.Frame(countdown_window)
        content_frame.pack(fill="both", expand=True, padx=20)
        
        tk.Label(content_frame, text=f"Successfully updated to version {new_version}!", 
                font=("Arial", 12, "bold"), fg="#27ae60").pack(pady=10)
        
        tk.Label(content_frame, text="The application will restart automatically in:", 
                font=("Arial", 11)).pack(pady=5)
        
        # Countdown label
        countdown_label = tk.Label(content_frame, text="5", 
                                  font=("Arial", 24, "bold"), fg="#e74c3c")
        countdown_label.pack(pady=15)
        
        # Buttons
        button_frame = tk.Frame(content_frame)
        button_frame.pack(fill="x", pady=10)
        
        tk.Button(button_frame, text="Restart Now", 
                 bg="#27ae60", fg="white", font=("Arial", 11, "bold"),
                 command=lambda: self.restart_from_countdown(countdown_window)).pack(side="left", padx=(0, 10))
        
        tk.Button(button_frame, text="Cancel", 
                 bg="#95a5a6", fg="white", font=("Arial", 11),
                 command=countdown_window.destroy).pack(side="left")
        
        # Start countdown
        self.countdown_value = 5
        self.countdown_active = True
        
        def update_countdown():
            if self.countdown_active and self.countdown_value > 0:
                countdown_label.config(text=str(self.countdown_value))
                self.countdown_value -= 1
                countdown_window.after(1000, update_countdown)
            elif self.countdown_active:
                # Countdown finished, restart
                self.restart_from_countdown(countdown_window)
        
        # Handle window close
        def on_close():
            self.countdown_active = False
            countdown_window.destroy()
        
        countdown_window.protocol("WM_DELETE_WINDOW", on_close)
        
        # Start the countdown
        update_countdown()
    
    def restart_from_countdown(self, countdown_window):
        """Restart application from countdown dialog"""
        self.countdown_active = False
        countdown_window.destroy()
        self.restart_application()
    
    def restart_application(self):
        """Restart the application"""
        try:
            # Save current state
            self.save_settings()
            
            # Get the script path
            script_path = os.path.abspath(__file__)
            
            # Log the restart attempt
            self.log_status("Restarting application...")
            
            # Close current application gracefully
            self.root.quit()
            
            # Use subprocess to restart (more reliable than os.execv on Windows)
            if getattr(sys, 'frozen', False):
                # If running as exe
                subprocess.Popen([sys.executable])
            else:
                # If running as Python script
                subprocess.Popen([sys.executable, script_path])
            
            # Exit current process
            sys.exit(0)
                
        except Exception as e:
            try:
                messagebox.showerror("Restart Failed", f"Failed to restart application: {e}\n\nPlease restart manually.")
            except:
                pass
            sys.exit(0)
    
    def show_changelog(self):
        """Show changelog window"""
        try:
            # Always get changelog from GitHub - never use local files
            import time
            cache_buster = int(time.time())
            url_with_cache_buster = f"{self.version_url}?t={cache_buster}"
            self.log_status(f"Fetching changelog from GitHub: {url_with_cache_buster}")
            response = requests.get(url_with_cache_buster, timeout=10)
            if response.status_code == 200:
                remote_data = response.json()
                version_history = remote_data.get("version_history", [])
            else:
                # If GitHub fails, show error instead of using local files
                messagebox.showerror("Changelog Error", f"Failed to fetch changelog from GitHub: HTTP {response.status_code}")
                return
        except Exception as e:
            messagebox.showerror("Changelog Error", f"Failed to fetch changelog from GitHub: {e}")
            return
        
        # Create changelog window
        changelog_window = tk.Toplevel(self.root)
        changelog_window.title("Changelog")
        changelog_window.geometry("600x500")
        changelog_window.resizable(True, True)
        
        # Header
        header_frame = tk.Frame(changelog_window, bg="#34495e")
        header_frame.pack(fill="x")
        
        tk.Label(header_frame, text="Version History", 
                font=("Arial", 16, "bold"), fg="white", bg="#34495e").pack(pady=10)
        
        # Changelog content
        text_frame = tk.Frame(changelog_window)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        changelog_text = tk.Text(text_frame, wrap="word", font=("Arial", 10))
        scrollbar = tk.Scrollbar(text_frame, command=changelog_text.yview)
        changelog_text.config(yscrollcommand=scrollbar.set)
        
        changelog_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Add version history
        for version_info in reversed(version_history):  # Show newest first
            version = version_info.get("version", "Unknown")
            release_date = version_info.get("release_date", "Unknown")
            changes = version_info.get("changelog", [])
            
            changelog_text.insert("end", f"Version {version} ({release_date})\n", "version_header")
            changelog_text.insert("end", "=" * 50 + "\n\n")
            
            if changes:
                for change in changes:
                    changelog_text.insert("end", f"• {change}\n")
            else:
                changelog_text.insert("end", "• No changelog available\n")
            
            changelog_text.insert("end", "\n\n")
        
        # Configure text tags
        changelog_text.tag_config("version_header", font=("Arial", 12, "bold"), foreground="#2c3e50")
        changelog_text.config(state="disabled")
        
        # Close button
        tk.Button(changelog_window, text="Close", command=changelog_window.destroy,
                 bg="#95a5a6", fg="white", font=("Arial", 11)).pack(pady=10)
    
    def show_about(self):
        """Show about dialog"""
        about_text = f"""RUST BM AFK Tool v{self.current_version}

What this tool does:
• Adds hours to your Rust account automatically
• Farms hours while you're away from computer
• Builds legit looking gaming profiles
• Join high hour requirement groups and servers
• Works with any Rust server via Battlemetrics

Key Features:
• Multiple server support with auto-switching
• Smart AFK detection avoidance
• Automatic updates
• Safe and undetectable operation
• Easy setup and use

Perfect for building up your Rust profile hours!

GitHub: github.com/{self.github_repo}
Discord: https://discord.gg/a5T2xBhKgt"""
        
        messagebox.showinfo("About RUST BM AFK Tool", about_text)
    
    def load_servers(self):
        """Load servers from JSON file"""
        servers_file = os.path.join(self.data_folder, "servers.json")
        try:
            if os.path.exists(servers_file):
                with open(servers_file, "r") as f:
                    servers = json.load(f)
                    self.log_status(f"Loaded {len(servers)} servers from servers.json")
                    self.log_status("Update system: Cache-busting enabled for immediate GitHub updates")
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
    
    def ping_server(self, server_ip, timeout=5):
        """Check if a server host is reachable (NOT if Rust server is actually running)"""
        try:
            # Parse IP and port
            if ':' in server_ip:
                ip, port = server_ip.split(':')
                port = int(port)
            else:
                ip = server_ip
                port = 28015  # Default Rust port
            
            # Method 1: Try to resolve hostname (for domain-based servers)
            try:
                socket.gethostbyname(ip)
            except socket.gaierror:
                return False  # Can't resolve hostname
            
            # Method 2: Try UDP ping on the game port (Rust uses UDP)
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(timeout)
                # Send a simple UDP packet
                sock.sendto(b'\x00', (ip, port))
                sock.close()
                # If no exception, server is likely reachable
                return True
            except Exception as e:
                print(f"Error in UDP ping for {ip}:{port}: {e}")
                pass
            
            # Method 3: Try TCP connection on query port (usually game_port + 1)
            try:
                query_port = port + 1
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((ip, query_port))
                sock.close()
                if result == 0:
                    return True
            except Exception as e:
                print(f"Error in TCP ping for {ip}:{query_port}: {e}")
                pass
            
            # Method 4: Try ICMP ping to the IP
            try:
                import subprocess
                import platform
                
                # Use system ping command
                param = '-n' if platform.system().lower() == 'windows' else '-c'
                command = ['ping', param, '1', '-w', str(timeout * 1000), ip]
                
                result = subprocess.run(command, capture_output=True, text=True, timeout=timeout + 2)
                return result.returncode == 0
            except Exception as e:
                print(f"Error in ICMP ping for {ip}: {e}")
                pass
            
            return False  # All methods failed
            
        except Exception as e:
            print(f"Error in ping_server for {server_ip}: {e}")
            return False
    
    def check_server_battlemetrics(self, server_ip, timeout=10, server_name=None, max_retries=2):
        """Check server status using Battlemetrics API - definitive validation"""
        rate_limited = False
        try:
            # Use the enhanced search from get_server_info_battlemetrics
            server_info, was_rate_limited = self.get_server_info_battlemetrics(server_ip, timeout, server_name=server_name, max_retries=max_retries)
            rate_limited = was_rate_limited
            
            if server_info:
                # Found server on BattleMetrics, check status
                status = server_info.get('status')
                result = status == 'online'
            else:
                # Server not found on BattleMetrics = server is not valid/online
                if not hasattr(self, '_bulk_validation_mode') or not self._bulk_validation_mode:
                    self.log_status(f"Server {server_ip} not found on BattleMetrics - marking as offline")
                result = False
            
            # Store rate limiting info for adaptive system
            if hasattr(self, '_current_server_data'):
                self._current_server_data['_rate_limited'] = rate_limited
                
            return result
                
        except Exception as e:
            # API method failed = cannot verify server status
            if not hasattr(self, '_bulk_validation_mode') or not self._bulk_validation_mode:
                self.log_status(f"BattleMetrics check failed for {server_ip}: {e} - marking as offline")
            
            # Store rate limiting info for adaptive system
            if hasattr(self, '_current_server_data'):
                self._current_server_data['_rate_limited'] = rate_limited
                
            return False
    
    def get_server_info_battlemetrics(self, server_ip, timeout=10, server_name=None, max_retries=2):
        """Get detailed server information from Battlemetrics API with retry logic"""
        was_rate_limited = False
        try:
            # Parse IP and port
            if ':' in server_ip:
                original_ip, port = server_ip.split(':')
            else:
                original_ip = server_ip
                port = "28015"
            
            # Try to resolve domain name to IP if it's a domain
            resolved_ip = original_ip
            is_domain = False
            
            # Check if it's a domain name (contains letters)
            if not original_ip.replace('.', '').replace('-', '').isdigit():
                is_domain = True
                try:
                    resolved_ip = socket.gethostbyname(original_ip)
                    self.log_status(f"Resolved {original_ip} to {resolved_ip}")
                except socket.gaierror:
                    self.log_status(f"Could not resolve domain {original_ip}")
                    resolved_ip = original_ip
            
            def extract_server_info(server):
                """Helper function to extract server info - ONLY fields we want to update"""
                attributes = server.get('attributes', {})
                details = attributes.get('details', {})
                
                # Determine premium status based on server name
                server_name = attributes.get('name', '').lower()
                premium_indicators = [
                    'rustafied', 'rusty moose', 'rusticated', 'facepunch'
                ]
                is_premium = any(indicator in server_name for indicator in premium_indicators)
                
                # ONLY return the fields we want to update:
                # - name, premium, official, modded, country, status, rust_type
                return {
                    'name': attributes.get('name', 'Unknown'),
                    'status': attributes.get('status'),
                    'country': attributes.get('country'),
                    'official': details.get('official', False),
                    'premium': is_premium,
                    'modded': details.get('modded', False),
                    'rust_type': details.get('rust_type'),
                }
            
            # Try multiple search strategies
            search_attempts = []
            
            # 1. Search by resolved IP (most likely to work for domains)
            if resolved_ip != original_ip:
                search_attempts.append(('resolved_ip', resolved_ip))
            
            # 2. Search by original input (in case it's already an IP)
            search_attempts.append(('original', original_ip))
            
            # 3. If it's a domain, try searching by domain parts in server names
            if is_domain:
                domain_parts = original_ip.lower().split('.')
                # Use the most distinctive part of the domain for search
                for part in domain_parts:
                    if len(part) > 3 and part not in ['com', 'net', 'org', 'gg', 'co']:
                        search_attempts.append(('domain_part', part))
                        break
            
            # 4. If we have the server name from our database, try searching by name parts
            if server_name:
                # Extract meaningful words from server name for search
                # Clean up the server name: remove brackets, pipes, apostrophes, and other special chars
                cleaned_name = re.sub(r"['\[\]|&\-_]", ' ', server_name.lower())
                name_words = cleaned_name.split()
                distinctive_words = []
                
                # Filter out common words and keep distinctive ones
                common_words = {'us', 'eu', 'na', 'server', 'rust', 'the', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'x', 'solo', 'duo', 'trio', 'quad', 'max', 'main', 'large', 'small', 'medium'}
                for word in name_words:
                    # Remove any remaining special characters and check if it's a meaningful word
                    clean_word = re.sub(r'[^a-z0-9]', '', word)
                    if len(clean_word) > 3 and clean_word not in common_words and not clean_word.isdigit() and not re.match(r'^\d+x?$', clean_word):
                        distinctive_words.append(clean_word)
                
                # Add the most distinctive words as search terms
                for word in distinctive_words[:3]:  # Try up to 3 distinctive words
                    search_attempts.append(('server_name_part', word))
            
            for search_type, search_term in search_attempts:
                # Only log search attempts if not in bulk validation mode
                if not hasattr(self, '_bulk_validation_mode') or not self._bulk_validation_mode:
                    self.log_status(f"Searching BattleMetrics for {search_term} (method: {search_type})")
                
                # Retry logic for each search attempt
                for retry_count in range(max_retries + 1):
                    try:
                        search_url = f"https://api.battlemetrics.com/servers"
                        params = {
                            'filter[game]': 'rust',
                            'filter[search]': search_term,
                            'page[size]': 50  # Increased to get more results
                        }
                        
                        response = requests.get(search_url, params=params, timeout=timeout)
                        
                        # Handle rate limiting with exponential backoff
                        if response.status_code == 429:
                            was_rate_limited = True
                            if retry_count < max_retries:
                                wait_time = 30 * (2 ** retry_count)  # 30s, 60s exponential backoff
                                if not hasattr(self, '_bulk_validation_mode') or not self._bulk_validation_mode:
                                    self.log_status(f"Rate limited - retry {retry_count + 1}/{max_retries + 1} in {wait_time}s...")
                                time.sleep(wait_time)
                                continue
                            else:
                                # Max retries reached, skip this search
                                if not hasattr(self, '_bulk_validation_mode') or not self._bulk_validation_mode:
                                    self.log_status(f"Rate limited - max retries reached for {search_term}")
                                break
                        
                        # Success - break out of retry loop
                        break
                        
                    except requests.exceptions.RequestException as e:
                        if retry_count < max_retries:
                            wait_time = 10 * (retry_count + 1)  # 10s, 20s for network errors
                            if not hasattr(self, '_bulk_validation_mode') or not self._bulk_validation_mode:
                                self.log_status(f"Network error - retry {retry_count + 1}/{max_retries + 1} in {wait_time}s: {e}")
                            time.sleep(wait_time)
                            continue
                        else:
                            # Max retries reached
                            if not hasattr(self, '_bulk_validation_mode') or not self._bulk_validation_mode:
                                self.log_status(f"Network error - max retries reached: {e}")
                            break
                
                # Skip processing if we couldn't get a successful response
                if 'response' not in locals() or response.status_code != 200:
                    continue
                
                if response.status_code == 200:
                    data = response.json()
                    servers = data.get('data', [])
                    
                    self.log_status(f"Found {len(servers)} potential matches for {search_term}")
                    
                    # Strategy 1: Look for exact IP:port match
                    for server in servers:
                        attributes = server.get('attributes', {})
                        server_ip_attr = attributes.get('ip')
                        server_port_attr = str(attributes.get('port', ''))
                        
                        # Check against both resolved and original IP
                        if ((server_ip_attr == resolved_ip or server_ip_attr == original_ip) 
                            and server_port_attr == port):
                            self.log_status(f"Found exact IP:port match: {server_ip_attr}:{server_port_attr}")
                            return extract_server_info(server), was_rate_limited
                    
                    # Strategy 2: If searching by domain part, look for name matches
                    if search_type == 'domain_part' and is_domain:
                        domain_parts = original_ip.lower().split('.')
                        for server in servers:
                            attributes = server.get('attributes', {})
                            server_name = attributes.get('name', '').lower()
                            server_port_attr = str(attributes.get('port', ''))
                            
                            # Check if server name contains domain parts and port matches
                            if (server_port_attr == port and 
                                any(part in server_name for part in domain_parts if len(part) > 3)):
                                self.log_status(f"Found name match: {server_name} (port: {server_port_attr})")
                                return extract_server_info(server), was_rate_limited
                    
                    # Strategy 3: If searching by server name part, look for name and port matches
                    if search_type == 'server_name_part':
                        for server in servers:
                            attributes = server.get('attributes', {})
                            server_name = attributes.get('name', '').lower()
                            server_port_attr = str(attributes.get('port', ''))
                            
                            # Check if server name contains the search term and port matches
                            if server_port_attr == port and search_term in server_name:
                                self.log_status(f"Found server name match: {server_name} (port: {server_port_attr})")
                                return extract_server_info(server), was_rate_limited
                    
                    # Strategy 4: Port-only match as last resort (for name-based searches)
                    if search_type in ['domain_part', 'server_name_part'] and len(servers) > 0:
                        for server in servers:
                            attributes = server.get('attributes', {})
                            server_port_attr = str(attributes.get('port', ''))
                            
                            if server_port_attr == port:
                                self.log_status(f"Found port match as fallback: {attributes.get('name', 'Unknown')} (port: {server_port_attr})")
                                return extract_server_info(server), was_rate_limited
                
                # Small delay between search attempts to be nice to the API
                time.sleep(0.1)  # 0.1 second delay between search attempts
            
            # If all search attempts failed - reduce log verbosity
            # Only log if this is a manual validation, not during bulk operations
            if not hasattr(self, '_bulk_validation_mode') or not self._bulk_validation_mode:
                self.log_status(f"Could not find server {server_ip} on BattleMetrics after trying multiple search methods")
            return None, was_rate_limited
                
        except Exception as e:
            self.log_status(f"Error searching BattleMetrics for {server_ip}: {e}")
            return None, was_rate_limited
    
    def validate_servers(self):
        """Validate all servers and show results"""
        if not self.servers:
            messagebox.showinfo("No Servers", "No servers to validate.")
            return
        
        # Create validation window
        validation_window = tk.Toplevel(self.root)
        validation_window.title("Server Validation")
        validation_window.geometry("750x650")
        validation_window.resizable(True, True)
        validation_window.minsize(600, 500)  # Set minimum size
        
        # Method selection frame
        method_frame = tk.LabelFrame(validation_window, text="Validation Method", padx=10, pady=5)
        method_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        validation_method = tk.StringVar(value="battlemetrics")
        tk.Radiobutton(method_frame, text="Quick Ping (Fast, but unreliable - only checks host reachability)", 
                      variable=validation_method, value="ping").pack(anchor="w", pady=2)
        tk.Radiobutton(method_frame, text="BattleMetrics API (Recommended - verifies actual server status)", 
                      variable=validation_method, value="battlemetrics").pack(anchor="w", pady=2)
        
        # Progress frame
        progress_frame = tk.LabelFrame(validation_window, text="Progress", padx=10, pady=5)
        progress_frame.pack(fill="x", padx=10, pady=5)
        
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, maximum=len(self.servers))
        progress_bar.pack(fill="x", pady=5)
        
        status_label = tk.Label(progress_frame, text="Click 'Start Validation' to begin...", font=("Arial", 10))
        status_label.pack(pady=2)
        
        # Timing info frame
        timing_frame = tk.Frame(progress_frame)
        timing_frame.pack(fill="x", pady=5)
        
        elapsed_label = tk.Label(timing_frame, text="Elapsed: 00:00", font=("Arial", 9))
        elapsed_label.pack(side="left", padx=10)
        
        avg_time_label = tk.Label(timing_frame, text="Avg per server: --", font=("Arial", 9))
        avg_time_label.pack(side="left", padx=10)
        
        eta_label = tk.Label(timing_frame, text="ETA: --", font=("Arial", 9))
        eta_label.pack(side="left", padx=10)
        
        # Stop button
        stop_btn = tk.Button(timing_frame, text="Stop", bg="#dc3545", fg="white", 
                            font=("Arial", 9, "bold"), state="disabled")
        stop_btn.pack(side="right", padx=10)
        
        # Results frame
        results_frame = tk.LabelFrame(validation_window, text="Validation Results", padx=5, pady=5)
        results_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Results text with scrollbar
        text_frame = tk.Frame(results_frame)
        text_frame.pack(fill="both", expand=True)
        
        results_text = tk.Text(text_frame, font=("Consolas", 9), wrap="none", height=15)
        v_scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=results_text.yview)
        h_scrollbar = tk.Scrollbar(text_frame, orient="horizontal", command=results_text.xview)
        results_text.config(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        results_text.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        
        # Bottom frame for statistics and buttons
        bottom_frame = tk.Frame(validation_window)
        bottom_frame.pack(fill="x", padx=10, pady=10, side="bottom")
        
        # Statistics frame
        stats_frame = tk.LabelFrame(bottom_frame, text="Statistics", padx=10, pady=5)
        stats_frame.pack(fill="x", pady=(0, 10))
        
        stats_container = tk.Frame(stats_frame)
        stats_container.pack()
        
        online_label = tk.Label(stats_container, text="Online: 0", font=("Arial", 11, "bold"), fg="green")
        online_label.pack(side="left", padx=15)
        
        offline_label = tk.Label(stats_container, text="Offline: 0", font=("Arial", 11, "bold"), fg="red")
        offline_label.pack(side="left", padx=15)
        
        total_label = tk.Label(stats_container, text=f"Total: {len(self.servers)}", font=("Arial", 11, "bold"))
        total_label.pack(side="left", padx=15)
        
        # Action buttons frame
        buttons_frame = tk.Frame(bottom_frame)
        buttons_frame.pack(pady=5)
        
        start_btn = tk.Button(buttons_frame, text="Start Validation", 
                             bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        start_btn.pack(side="left", padx=5, pady=5)
        
        remove_offline_btn = tk.Button(buttons_frame, text="Remove Offline Servers", 
                                      bg="#8B0000", fg="white", font=("Arial", 10, "bold"),
                                      state="disabled")
        remove_offline_btn.pack(side="left", padx=5, pady=5)
        
        update_info_btn = tk.Button(buttons_frame, text="Update Server Info", 
                                   bg="#FF8C00", fg="white", font=("Arial", 10, "bold"))
        update_info_btn.pack(side="left", padx=5, pady=5)
        
        close_btn = tk.Button(buttons_frame, text="Close", command=validation_window.destroy,
                             bg="#6c757d", fg="white", font=("Arial", 10, "bold"))
        close_btn.pack(side="left", padx=5, pady=5)
        
        # Update server info function
        def update_server_info():
            if not self.servers:
                return
            
            # Check if already updating
            if hasattr(update_server_info, 'is_running') and update_server_info.is_running:
                return
            
            # Set running flag and stop flag
            update_server_info.is_running = True
            update_server_info.stop_requested = False
            
            # Stop function for update process
            def stop_update():
                update_server_info.stop_requested = True
                stop_btn.config(state="disabled", text="Stopping...")
                status_label.config(text="Stopping server update...")
            
            # Disable buttons during update
            start_btn.config(state="disabled")
            update_info_btn.config(state="disabled", text="Updating...")
            stop_btn.config(state="normal", command=stop_update)
            remove_offline_btn.config(state="disabled")
            
            progress_var.set(0)
            results_text.delete(1.0, tk.END)
            status_label.config(text="Starting server info update...")
            
            # Reset timing labels for update
            elapsed_label.config(text="Elapsed: 00:00")
            avg_time_label.config(text="Avg per server: --")
            eta_label.config(text="ETA: --")
            
            def update_thread():
                update_start_time = time.time()
                updated_servers = []
                found_count = 0
                completed_updates = 0
                
                # Check if window still exists before updating
                def safe_update_gui(func):
                    try:
                        if validation_window.winfo_exists():
                            func()
                    except tk.TclError:
                        pass  # Window was closed, ignore
                
                def update_timing_info_update():
                    elapsed = time.time() - update_start_time
                    elapsed_str = f"{int(elapsed//60):02d}:{int(elapsed%60):02d}"
                    validation_window.after(0, lambda: safe_update_gui(lambda: elapsed_label.config(text=f"Elapsed: {elapsed_str}")))
                    
                    if completed_updates > 0:
                        avg_time = elapsed / completed_updates
                        avg_str = f"{avg_time:.1f}s"
                        validation_window.after(0, lambda: safe_update_gui(lambda: avg_time_label.config(text=f"Avg per server: {avg_str}")))
                        
                        remaining_servers = len(self.servers) - completed_updates
                        if remaining_servers > 0:
                            eta_seconds = remaining_servers * avg_time
                            eta_str = f"{int(eta_seconds//60):02d}:{int(eta_seconds%60):02d}"
                            validation_window.after(0, lambda: safe_update_gui(lambda: eta_label.config(text=f"ETA: {eta_str}")))
                        else:
                            validation_window.after(0, lambda: safe_update_gui(lambda: eta_label.config(text="ETA: Complete")))
                
                # Add header
                validation_window.after(0, lambda: safe_update_gui(lambda: results_text.insert(tk.END, "Updating Server Information from BattleMetrics API\n")))
                validation_window.after(0, lambda: safe_update_gui(lambda: results_text.insert(tk.END, "STATUS   | SERVER NAME\n")))
                validation_window.after(0, lambda: safe_update_gui(lambda: results_text.insert(tk.END, "-" * 50 + "\n")))
                
                for i, server in enumerate(self.servers):
                    # Check if stop was requested
                    if update_server_info.stop_requested:
                        validation_window.after(0, lambda: safe_update_gui(lambda: status_label.config(text="Server update stopped by user")))
                        break
                    
                    server_name = server.get('name', 'Unknown')
                    server_ip = server.get('ip', '')
                    
                    # Update status with progress
                    validation_window.after(0, lambda name=server_name, idx=i: safe_update_gui(lambda: status_label.config(text=f"Updating {name}... ({idx + 1}/{len(self.servers)})")))
                    
                    # Update timing info
                    update_timing_info_update()
                    
                    # Get detailed server info from BattleMetrics with retry logic
                    server_info = None
                    max_retries = 3
                    for retry in range(max_retries):
                        # Check if stop was requested during retries
                        if update_server_info.stop_requested:
                            break
                            
                        server_info = self.get_server_info_battlemetrics(server_ip, timeout=15, server_name=server_name)
                        if server_info is not None:
                            break
                        elif retry < max_retries - 1:
                            # Wait longer between retries to avoid rate limiting
                            for sleep_second in range(5):
                                if update_server_info.stop_requested:
                                    break
                                time.sleep(1)
                            validation_window.after(0, lambda name=server_name, r=retry: safe_update_gui(lambda: status_label.config(text=f"Retrying {name}... (attempt {r+2})")))
                    
                    # Skip processing if stop was requested
                    if update_server_info.stop_requested:
                        break
                    
                    if server_info is None:
                        validation_window.after(0, lambda name=server_name: safe_update_gui(lambda: status_label.config(text=f"Failed to get info for {name} after {max_retries} attempts")))
                    
                    # Increment completed counter
                    completed_updates += 1
                    
                    if server_info:
                        found_count += 1
                        
                        # Update server with new information (only specific fields)
                        updated_server = server.copy()
                        
                        # Only update these specific fields from BattleMetrics:
                        # - name (if BattleMetrics has a better name)
                        # - premium status
                        # - official status  
                        # - modded status
                        # - country
                        # - status (online/offline)
                        # - rust_type
                        
                        updated_fields = []
                        
                        # Update name if BattleMetrics has a different/better name
                        if server_info.get('name') and server_info['name'] != 'Unknown' and server_info['name'] != updated_server.get('name'):
                            old_name = updated_server.get('name', 'Unknown')
                            updated_server['name'] = server_info['name']
                            updated_fields.append(f"name: '{old_name}' -> '{server_info['name']}'")
                        
                        # Update only the allowed fields
                        if server_info.get('premium') is not None and server_info.get('premium') != updated_server.get('premium'):
                            old_premium = updated_server.get('premium', False)
                            updated_server['premium'] = server_info.get('premium', False)
                            updated_fields.append(f"premium: {old_premium} -> {server_info.get('premium', False)}")
                        
                        if server_info.get('official') is not None and server_info.get('official') != updated_server.get('official'):
                            old_official = updated_server.get('official', False)
                            updated_server['official'] = server_info.get('official', False)
                            updated_fields.append(f"official: {old_official} -> {server_info.get('official', False)}")
                        
                        if server_info.get('modded') is not None and server_info.get('modded') != updated_server.get('modded'):
                            old_modded = updated_server.get('modded', False)
                            updated_server['modded'] = server_info.get('modded', False)
                            updated_fields.append(f"modded: {old_modded} -> {server_info.get('modded', False)}")
                        
                        if server_info.get('country') and server_info.get('country') != updated_server.get('country'):
                            old_country = updated_server.get('country', 'Unknown')
                            updated_server['country'] = server_info.get('country')
                            updated_fields.append(f"country: '{old_country}' -> '{server_info.get('country')}'")
                        
                        if server_info.get('status') and server_info.get('status') != updated_server.get('status'):
                            old_status = updated_server.get('status', 'Unknown')
                            updated_server['status'] = server_info.get('status')
                            updated_fields.append(f"status: '{old_status}' -> '{server_info.get('status')}'")
                        
                        if server_info.get('rust_type') and server_info.get('rust_type') != updated_server.get('rust_type'):
                            old_rust_type = updated_server.get('rust_type', 'Unknown')
                            updated_server['rust_type'] = server_info.get('rust_type')
                            updated_fields.append(f"rust_type: '{old_rust_type}' -> '{server_info.get('rust_type')}'")
                        
                        # Always update the last update timestamp
                        updated_server['last_info_update'] = time.strftime('%Y-%m-%d %H:%M:%S')
                        
                        # Log what fields were updated
                        if updated_fields:
                            self.log_status(f"Updated {server_name}: {', '.join(updated_fields)}")
                        else:
                            self.log_status(f"No changes needed for {server_name} - all fields up to date")
                        
                        # Preserve all other existing fields (ip, battlemetrics_id, pve, rank, map, max_players, etc.)
                        
                        # Format display info (simplified since we don't get player/rank data)
                        players_info = "N/A"  # We don't fetch this data anymore
                        rank_info = "N/A"     # We don't fetch this data anymore
                        status_info = "UPDATED"
                        
                        # Show official/premium indicators (use updated server data)
                        indicators = []
                        if updated_server.get('official'):
                            indicators.append("OFFICIAL")
                        if updated_server.get('premium'):
                            indicators.append("PREMIUM")
                        if updated_server.get('modded'):
                            indicators.append("MODDED")
                        # Don't show PVE since we're not updating that field
                        
                        indicator_text = f" [{', '.join(indicators)}]" if indicators else ""
                        
                        result_line = f"{status_info:<8} | {updated_server['name']}{indicator_text}\n"
                        
                        updated_servers.append(updated_server)
                        
                    else:
                        # Keep original server if not found on BattleMetrics
                        result_line = f"{'NOT FOUND':<8} | {server_name}\n"
                        updated_servers.append(server)
                    
                    # Update results display
                    def update_results(line):
                        results_text.insert(tk.END, line)
                        results_text.see(tk.END)
                    
                    validation_window.after(0, lambda line=result_line: safe_update_gui(lambda: update_results(line)))
                    
                    # Update progress
                    validation_window.after(0, lambda: safe_update_gui(lambda: progress_var.set(progress_var.get() + 1)))
                    
                    # Rate limiting - be nice to the API
                    if i < len(self.servers) - 1 and not update_server_info.stop_requested:
                        # Break the sleep into smaller chunks so we can respond to stop requests
                        for sleep_second in range(3):
                            if update_server_info.stop_requested:
                                break
                            time.sleep(1)
                
                # Save updated servers (only if not stopped)
                if not update_server_info.stop_requested:
                    self.servers = updated_servers
                    self.save_servers()
                    
                    # Update the main server list display
                    validation_window.after(0, lambda: safe_update_gui(lambda: self.update_server_list()))
                
                # Calculate final timing
                total_elapsed = time.time() - update_start_time
                elapsed_str = f"{int(total_elapsed//60):02d}:{int(total_elapsed%60):02d}"
                
                # Update final status based on whether it was stopped or completed
                if update_server_info.stop_requested:
                    validation_window.after(0, lambda: safe_update_gui(lambda: status_label.config(text=f"Update stopped by user after {elapsed_str} - {completed_updates} servers processed")))
                    self.log_status(f"Server update stopped by user after {elapsed_str} - {completed_updates} servers processed")
                else:
                    validation_window.after(0, lambda: safe_update_gui(lambda: status_label.config(text=f"Update complete! Found {found_count}/{len(self.servers)} servers in {elapsed_str}")))
                    self.log_status(f"Updated server info for {found_count}/{len(self.servers)} servers from BattleMetrics")
                
                validation_window.after(0, lambda: safe_update_gui(lambda: eta_label.config(text="ETA: Complete")))
                validation_window.after(0, lambda: safe_update_gui(lambda: start_btn.config(state="normal")))
                validation_window.after(0, lambda: safe_update_gui(lambda: update_info_btn.config(state="normal", text="Update Server Info")))
                validation_window.after(0, lambda: safe_update_gui(lambda: stop_btn.config(state="disabled", text="Stop")))
                
                # Clear running flag
                update_server_info.is_running = False
            
            # Start update thread
            update_thread_obj = threading.Thread(target=update_thread, daemon=True)
            update_thread_obj.start()
        
        # Validation control variables
        validation_start_time = None
        validation_stop_requested = False
        completed_servers = 0
        
        def stop_validation():
            nonlocal validation_stop_requested
            validation_stop_requested = True
            stop_btn.config(state="disabled", text="Stopping...")
            status_label.config(text="Stopping validation...")
        
        def update_timing_info():
            if validation_start_time is None:
                return
            
            elapsed = time.time() - validation_start_time
            elapsed_str = f"{int(elapsed//60):02d}:{int(elapsed%60):02d}"
            elapsed_label.config(text=f"Elapsed: {elapsed_str}")
            
            if completed_servers > 0:
                avg_time = elapsed / completed_servers
                avg_str = f"{avg_time:.1f}s"
                avg_time_label.config(text=f"Avg per server: {avg_str}")
                
                remaining_servers = len(self.servers) - completed_servers
                if remaining_servers > 0:
                    eta_seconds = remaining_servers * avg_time
                    eta_str = f"{int(eta_seconds//60):02d}:{int(eta_seconds%60):02d}"
                    eta_label.config(text=f"ETA: {eta_str}")
                else:
                    eta_label.config(text="ETA: Complete")
            
            # Schedule next update if validation is still running
            if not validation_stop_requested and completed_servers < len(self.servers):
                validation_window.after(1000, update_timing_info)
        
        # Start validation function
        def start_validation():
            nonlocal validation_start_time, validation_stop_requested, completed_servers
            
            # Reset timing variables
            validation_start_time = time.time()
            validation_stop_requested = False
            completed_servers = 0
            
            # Disable start button and reset progress
            start_btn.config(state="disabled", text="Validating...")
            stop_btn.config(state="normal", command=stop_validation)
            progress_var.set(0)
            results_text.delete(1.0, tk.END)
            online_label.config(text="Online: 0")
            offline_label.config(text="Offline: 0")
            remove_offline_btn.config(state="disabled")
            
            # Reset timing labels
            elapsed_label.config(text="Elapsed: 00:00")
            avg_time_label.config(text="Avg per server: --")
            eta_label.config(text="ETA: --")
            
            # Start timing updates
            update_timing_info()
            
            # Get selected method
            method = validation_method.get()
            
            def validate_thread():
                nonlocal completed_servers
                online_servers = []
                offline_servers = []
                
                # Set bulk validation mode to reduce logging verbosity
                self._bulk_validation_mode = True
                
                def validate_single_server(i, server):
                    nonlocal completed_servers
                    
                    # Check if stop was requested
                    if validation_stop_requested:
                        return None, i, server
                    
                    server_name = server.get('name', 'Unknown')
                    server_ip = server.get('ip', '')
                    
                    # Update status
                    validation_window.after(0, lambda: status_label.config(text=f"Testing {server_name}... ({completed_servers + 1}/{len(self.servers)})"))
                    
                    # Choose validation method
                    if method == "battlemetrics":
                        is_online = self.check_server_battlemetrics(server_ip, timeout=15, server_name=server_name, max_retries=2)
                        # Mark validation method used
                        server['_validation_method'] = 'battlemetrics'
                        server['_battlemetrics_found'] = is_online
                    else:
                        # Ping only checks if host is reachable, not if Rust server is actually running
                        is_online = self.ping_server(server_ip)
                        server['_validation_method'] = 'ping'
                        server['_battlemetrics_found'] = False
                    
                    # Check again if stop was requested during validation
                    if validation_stop_requested:
                        return None, i, server
                    
                    if is_online:
                        online_servers.append((i, server))
                        status = "ONLINE"
                        color = "green"
                    else:
                        offline_servers.append((i, server))
                        status = "OFFLINE"
                        color = "red"
                    
                    # Update results
                    result_line = f"{status:<8} | {server_name:<40} | {server_ip}\n"
                    
                    def update_results(line, status_tag):
                        results_text.insert(tk.END, line)
                        # Configure tag colors first
                        results_text.tag_config("online", foreground="green")
                        results_text.tag_config("offline", foreground="red")
                        # Get the line that was just inserted
                        line_start = f"{results_text.index(tk.END)}-2l"
                        line_end = f"{results_text.index(tk.END)}-1l"
                        # Apply the tag to the entire line
                        results_text.tag_add(status_tag, line_start, line_end)
                        results_text.see(tk.END)
                    
                    validation_window.after(0, lambda: update_results(result_line, status.lower()))
                    
                    # Update progress and completed counter
                    completed_servers += 1
                    validation_window.after(0, lambda: progress_var.set(completed_servers))
                    
                    # No delays here - handled by smart adaptive system
                    
                    return is_online, i, server
                
                # Add header
                method_name = "Battlemetrics API" if method == "battlemetrics" else "Network Ping"
                validation_window.after(0, lambda: results_text.insert(tk.END, f"Validation Method: {method_name}\n"))
                validation_window.after(0, lambda: results_text.insert(tk.END, "STATUS   | SERVER NAME                              | IP ADDRESS\n"))
                validation_window.after(0, lambda: results_text.insert(tk.END, "-" * 80 + "\n"))
                
                # Process servers based on validation method
                if method == "battlemetrics":
                    # Smart adaptive processing for BattleMetrics
                    api_performance = {
                        'success_count': 0,
                        'rate_limit_count': 0,
                        'error_count': 0,
                        'avg_response_time': 0,
                        'total_requests': 0,
                        'current_delay': 3.0,  # Start with 3 second delay
                        'batch_size': 1,  # Start with sequential
                        'consecutive_successes': 0
                    }
                    
                    def update_api_performance(success, rate_limited, response_time, error=False):
                        api_performance['total_requests'] += 1
                        if success:
                            api_performance['success_count'] += 1
                            api_performance['consecutive_successes'] += 1
                        else:
                            api_performance['consecutive_successes'] = 0
                            
                        if rate_limited:
                            api_performance['rate_limit_count'] += 1
                        if error:
                            api_performance['error_count'] += 1
                            
                        # Update average response time
                        if response_time > 0:
                            if api_performance['avg_response_time'] == 0:
                                api_performance['avg_response_time'] = response_time
                            else:
                                api_performance['avg_response_time'] = (api_performance['avg_response_time'] + response_time) / 2
                        
                        # Adaptive delay adjustment
                        success_rate = api_performance['success_count'] / api_performance['total_requests']
                        rate_limit_rate = api_performance['rate_limit_count'] / api_performance['total_requests']
                        
                        # Adjust delay based on performance
                        if rate_limit_rate > 0.2:  # More than 20% rate limited
                            api_performance['current_delay'] = min(api_performance['current_delay'] * 1.5, 10.0)
                        elif success_rate > 0.8 and api_performance['consecutive_successes'] >= 5:
                            # API is performing well, speed up
                            api_performance['current_delay'] = max(api_performance['current_delay'] * 0.8, 0.5)
                            
                        # Adjust batch size based on performance
                        if success_rate > 0.9 and rate_limit_rate < 0.1 and api_performance['consecutive_successes'] >= 10:
                            api_performance['batch_size'] = min(3, api_performance['batch_size'] + 1)
                        elif rate_limit_rate > 0.15 or api_performance['consecutive_successes'] < 3:
                            api_performance['batch_size'] = 1
                    
                    # Process servers with adaptive batching
                    i = 0
                    while i < len(self.servers) and not validation_stop_requested:
                        batch_end = min(i + api_performance['batch_size'], len(self.servers))
                        batch_servers = [(idx, self.servers[idx]) for idx in range(i, batch_end)]
                        
                        if api_performance['batch_size'] == 1:
                            # Sequential processing
                            for server_idx, server in batch_servers:
                                if validation_stop_requested:
                                    break
                                start_time = time.time()
                                try:
                                    result = validate_single_server(server_idx, server)
                                    response_time = time.time() - start_time
                                    
                                    if result:
                                        is_online, server_index, server_data = result
                                        rate_limited = hasattr(server_data, '_rate_limited') and server_data._rate_limited
                                        update_api_performance(True, rate_limited, response_time)
                                        
                                        if is_online:
                                            online_servers.append((server_index, server_data))
                                        else:
                                            offline_servers.append((server_index, server_data))
                                    else:
                                        update_api_performance(False, False, response_time, error=True)
                                        offline_servers.append((server_idx, server))
                                        
                                except Exception as e:
                                    response_time = time.time() - start_time
                                    update_api_performance(False, False, response_time, error=True)
                                    error_msg = f"Error validating server: {e}"
                                    print(error_msg)
                                    offline_servers.append((server_idx, server))
                                
                                # Adaptive delay
                                if server_idx < len(self.servers) - 1:  # Not the last server
                                    time.sleep(api_performance['current_delay'])
                        else:
                            # Batch processing with ThreadPoolExecutor
                            with concurrent.futures.ThreadPoolExecutor(max_workers=api_performance['batch_size']) as executor:
                                batch_futures = [executor.submit(validate_single_server, idx, server) for idx, server in batch_servers]
                                
                                for future in concurrent.futures.as_completed(batch_futures):
                                    if validation_stop_requested:
                                        for f in batch_futures:
                                            f.cancel()
                                        break
                                    try:
                                        result = future.result()
                                        if result:
                                            is_online, server_index, server_data = result
                                            rate_limited = hasattr(server_data, '_rate_limited') and server_data._rate_limited
                                            update_api_performance(True, rate_limited, 0)
                                            
                                            if is_online:
                                                online_servers.append((server_index, server_data))
                                            else:
                                                offline_servers.append((server_index, server_data))
                                        else:
                                            update_api_performance(False, False, 0, error=True)
                                    except Exception as e:
                                        update_api_performance(False, False, 0, error=True)
                                        error_msg = f"Error validating server: {e}"
                                        print(error_msg)
                            
                            # Delay between batches
                            if batch_end < len(self.servers):
                                time.sleep(api_performance['current_delay'])
                        
                        i = batch_end
                        
                        # Log performance every 10 servers
                        if i % 10 == 0 and not hasattr(self, '_bulk_validation_mode'):
                            success_rate = api_performance['success_count'] / max(api_performance['total_requests'], 1) * 100
                            self.log_status(f"API Performance: {success_rate:.1f}% success, delay: {api_performance['current_delay']:.1f}s, batch: {api_performance['batch_size']}")
                    
                    # Final performance summary
                    if not hasattr(self, '_bulk_validation_mode'):
                        success_rate = api_performance['success_count'] / max(api_performance['total_requests'], 1) * 100
                        rate_limit_rate = api_performance['rate_limit_count'] / max(api_performance['total_requests'], 1) * 100
                        self.log_status(f"Final API Performance: {success_rate:.1f}% success, {rate_limit_rate:.1f}% rate limited, avg delay: {api_performance['current_delay']:.1f}s")
                else:
                    # Use ThreadPoolExecutor for ping validation (lighter load)
                    max_workers = 10
                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                        futures = [executor.submit(validate_single_server, i, server) for i, server in enumerate(self.servers)]
                        
                        for future in concurrent.futures.as_completed(futures):
                            if validation_stop_requested:
                                # Cancel remaining futures
                                for f in futures:
                                    f.cancel()
                                break
                            try:
                                result = future.result()
                                if result:
                                    is_online, server_index, server_data = result
                                    if is_online:
                                        online_servers.append((server_index, server_data))
                                    else:
                                        offline_servers.append((server_index, server_data))
                            except Exception as e:
                                error_msg = f"Error validating server: {e}"
                                print(error_msg)
                                # Try to log to file if possible
                                try:
                                    with open(os.path.join("data", "afk_log.txt"), "a", encoding="utf-8") as f:
                                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        f.write(f"[{timestamp}] {error_msg}\n")
                                except:
                                    pass
                
                # Calculate final timing
                total_elapsed = time.time() - validation_start_time
                elapsed_str = f"{int(total_elapsed//60):02d}:{int(total_elapsed%60):02d}"
                
                # Update final statistics
                online_count = len(online_servers)
                offline_count = len(offline_servers)
                
                validation_window.after(0, lambda: online_label.config(text=f"Online: {online_count}"))
                validation_window.after(0, lambda: offline_label.config(text=f"Offline: {offline_count}"))
                
                if validation_stop_requested:
                    validation_window.after(0, lambda: status_label.config(text=f"Validation stopped! Tested {completed_servers}/{len(self.servers)} servers in {elapsed_str}"))
                    validation_window.after(0, lambda: eta_label.config(text="ETA: Stopped"))
                else:
                    validation_window.after(0, lambda: status_label.config(text=f"Validation complete! Tested {len(self.servers)} servers in {elapsed_str}"))
                    validation_window.after(0, lambda: eta_label.config(text="ETA: Complete"))
                
                validation_window.after(0, lambda: start_btn.config(state="normal", text="Start Validation"))
                validation_window.after(0, lambda: stop_btn.config(state="disabled", text="Stop"))
                
                # Reset bulk validation mode and log summary
                self._bulk_validation_mode = False
                
                # Log validation summary
                battlemetrics_online = sum(1 for _, server in online_servers if server.get('_validation_method') == 'battlemetrics')
                ping_online = sum(1 for _, server in online_servers if server.get('_validation_method') == 'ping')
                
                self.log_status(f"Validation complete: {online_count} online, {offline_count} offline")
                if battlemetrics_online > 0:
                    self.log_status(f"  - {battlemetrics_online} verified on BattleMetrics (reliable)")
                if ping_online > 0:
                    self.log_status(f"  - {ping_online} ping-responsive only (may not be actual Rust servers)")
                if offline_count > 0:
                    self.log_status(f"  - {offline_count} failed validation (offline or not found)")
                
                # Enable remove button if there are offline servers
                if offline_count > 0:
                    def remove_offline():
                        if messagebox.askyesno("Confirm Removal", 
                                             f"Are you sure you want to remove {offline_count} offline servers?\n\nThis action cannot be undone."):
                            # Remove offline servers (in reverse order to maintain indices)
                            for i, server in sorted(offline_servers, reverse=True):
                                del self.servers[i]
                            
                            self.save_servers()
                            self.update_server_list()
                            self.log_status(f"Removed {offline_count} offline servers")
                            validation_window.destroy()
                    
                    validation_window.after(0, lambda: remove_offline_btn.config(state="normal", command=remove_offline))
            
            # Start validation thread
            validation_thread = threading.Thread(target=validate_thread, daemon=True)
            validation_thread.start()
        
        # Connect buttons
        start_btn.config(command=start_validation)
        update_info_btn.config(command=update_server_info)
    

    

    def clear_log(self):
        """Clear the log display"""
        if hasattr(self, 'log_text'):
            self.log_text.delete(1.0, tk.END)
            self.log_status("Log cleared")
    
    def open_data_folder(self):
        """Open the data folder in file explorer"""
        import subprocess
        import platform
        
        try:
            if platform.system() == "Windows":
                subprocess.run(["explorer", self.data_folder])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", self.data_folder])
            else:  # Linux
                subprocess.run(["xdg-open", self.data_folder])
            self.log_status("Opened data folder")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open data folder: {e}")



    def show_update_available_dialog(self, version_info):
        """Show dialog when update is available"""
        remote_version = version_info.get("version", "Unknown")
        release_date = version_info.get("release_date", "Unknown")
        changelog = version_info.get("changelog", [])
        download_url = version_info.get("download_url", f"https://github.com/{self.github_repo}/releases/latest")
        
        # Check if auto-update is enabled
        if self.settings.get("auto_update", False):
            self.log_status(f"Auto-update enabled, installing version {remote_version} automatically...")
            self.start_update_process(None, version_info)
            return
        
        # Create update dialog
        update_window = tk.Toplevel(self.root)
        update_window.title("Update Available")
        update_window.geometry("500x400")
        update_window.resizable(False, False)
        update_window.grab_set()  # Make it modal
        
        # Center the window
        update_window.transient(self.root)
        update_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 200,
            self.root.winfo_rooty() + 100
        ))
        
        # Header
        header_frame = tk.Frame(update_window, bg="#4CAF50")
        header_frame.pack(fill="x", pady=(0, 20))
        
        tk.Label(header_frame, text="Update Available!", 
                font=("Arial", 16, "bold"), bg="#4CAF50", fg="white").pack(pady=15)
        
        # Content frame
        content_frame = tk.Frame(update_window)
        content_frame.pack(fill="both", expand=True, padx=20)
        
        # Version info
        version_frame = tk.Frame(content_frame)
        version_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(version_frame, text=f"Current Version: {self.current_version}", 
                font=("Arial", 11)).pack(anchor="w")
        tk.Label(version_frame, text=f"New Version: {remote_version}", 
                font=("Arial", 11, "bold"), fg="#4CAF50").pack(anchor="w")
        tk.Label(version_frame, text=f"Release Date: {release_date}", 
                font=("Arial", 10), fg="gray").pack(anchor="w")
        
        # Changelog
        if changelog:
            tk.Label(content_frame, text="What's New:", 
                    font=("Arial", 11, "bold")).pack(anchor="w", pady=(10, 5))
            
            changelog_frame = tk.Frame(content_frame)
            changelog_frame.pack(fill="both", expand=True)
            
            changelog_text = tk.Text(changelog_frame, height=8, wrap="word", 
                                   font=("Arial", 10), bg="#f5f5f5")
            scrollbar = tk.Scrollbar(changelog_frame, orient="vertical", command=changelog_text.yview)
            changelog_text.config(yscrollcommand=scrollbar.set)
            
            changelog_text.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Add changelog items
            for i, item in enumerate(changelog, 1):
                changelog_text.insert("end", f"• {item}\n")
            
            changelog_text.config(state="disabled")
        
        # Buttons
        button_frame = tk.Frame(update_window)
        button_frame.pack(fill="x", padx=20, pady=20)
        
        tk.Button(button_frame, text="Update Now", 
                 command=lambda: self.start_update_process(update_window, version_info),
                 bg="#4CAF50", fg="white", font=("Arial", 11, "bold"),
                 width=15).pack(side="right", padx=(10, 0))
        
        tk.Button(button_frame, text="View on GitHub", 
                 command=lambda: self.open_download_page(download_url, update_window),
                 bg="#3498db", fg="white", font=("Arial", 11),
                 width=12).pack(side="right", padx=(0, 10))
        
        tk.Button(button_frame, text="Later", 
                 command=update_window.destroy,
                 bg="#95a5a6", fg="white", font=("Arial", 11),
                 width=10).pack(side="right")
        
        self.log_status(f"Update available: v{remote_version} (current: v{self.current_version})")
    
    def open_download_page(self, download_url, dialog_window):
        """Open the download page in browser"""
        try:
            webbrowser.open(download_url)
            dialog_window.destroy()
            self.log_status("Opened download page in browser")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open download page:\n{str(e)}")
            self.log_status(f"Failed to open download page: {str(e)}")
    

    
    def show_background_update_dialog(self, version_info):
        """Show update dialog for background checks with 'Don't ask again' option"""
        remote_version = version_info.get("version", "Unknown")
        release_date = version_info.get("release_date", "Unknown")
        changelog = version_info.get("changelog", [])
        download_url = version_info.get("download_url", f"https://github.com/{self.github_repo}/releases/latest")
        
        # Check if auto-update is enabled
        if self.settings.get("auto_update", False):
            self.log_status(f"Auto-update enabled, installing version {remote_version} automatically...")
            self.start_update_process(None, version_info)
            return
        
        # Create update dialog
        update_window = tk.Toplevel(self.root)
        update_window.title("Update Available")
        update_window.geometry("520x450")
        update_window.resizable(False, False)
        update_window.grab_set()  # Make it modal
        
        # Center the window
        update_window.transient(self.root)
        update_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 190,
            self.root.winfo_rooty() + 90
        ))
        
        # Header
        header_frame = tk.Frame(update_window, bg="#4CAF50")
        header_frame.pack(fill="x", pady=(0, 20))
        
        tk.Label(header_frame, text="Update Available!", 
                font=("Arial", 16, "bold"), bg="#4CAF50", fg="white").pack(pady=15)
        
        # Content frame
        content_frame = tk.Frame(update_window)
        content_frame.pack(fill="both", expand=True, padx=20)
        
        # Version info
        version_frame = tk.Frame(content_frame)
        version_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(version_frame, text=f"Current Version: {self.current_version}", 
                font=("Arial", 11)).pack(anchor="w")
        tk.Label(version_frame, text=f"New Version: {remote_version}", 
                font=("Arial", 11, "bold"), fg="#4CAF50").pack(anchor="w")
        tk.Label(version_frame, text=f"Release Date: {release_date}", 
                font=("Arial", 10), fg="gray").pack(anchor="w")
        
        # Changelog
        if changelog:
            tk.Label(content_frame, text="What's New:", 
                    font=("Arial", 11, "bold")).pack(anchor="w", pady=(10, 5))
            
            changelog_frame = tk.Frame(content_frame)
            changelog_frame.pack(fill="both", expand=True)
            
            changelog_text = tk.Text(changelog_frame, height=8, wrap="word", 
                                   font=("Arial", 10), bg="#f5f5f5")
            scrollbar = tk.Scrollbar(changelog_frame, orient="vertical", command=changelog_text.yview)
            changelog_text.config(yscrollcommand=scrollbar.set)
            
            changelog_text.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Add changelog items
            for i, item in enumerate(changelog, 1):
                changelog_text.insert("end", f"• {item}\n")
            
            changelog_text.config(state="disabled")
        
        # Don't ask again checkbox
        dont_ask_frame = tk.Frame(update_window)
        dont_ask_frame.pack(fill="x", padx=20, pady=(10, 0))
        
        dont_ask_var = tk.BooleanVar()
        tk.Checkbutton(dont_ask_frame, text="Don't check for updates automatically", 
                      variable=dont_ask_var, font=("Arial", 9)).pack(anchor="w")
        
        # Buttons
        button_frame = tk.Frame(update_window)
        button_frame.pack(fill="x", padx=20, pady=20)
        
        def on_download():
            if dont_ask_var.get():
                self.settings["auto_check_updates"] = False
                self.auto_check_updates_var.set(False)
                self.save_settings()
                self.log_status("Automatic update checking disabled by user")
            self.start_update_process(update_window, version_info)
        
        def on_later():
            if dont_ask_var.get():
                self.settings["auto_check_updates"] = False
                self.auto_check_updates_var.set(False)
                self.save_settings()
                self.log_status("Automatic update checking disabled by user")
            update_window.destroy()
        
        tk.Button(button_frame, text="Update Now", 
                 command=on_download,
                 bg="#4CAF50", fg="white", font=("Arial", 11, "bold"),
                 width=15).pack(side="right", padx=(10, 0))
        
        tk.Button(button_frame, text="View on GitHub", 
                 command=lambda: self.open_download_page(download_url, update_window),
                 bg="#3498db", fg="white", font=("Arial", 11),
                 width=12).pack(side="right", padx=(0, 10))
        
        tk.Button(button_frame, text="Later", 
                 command=on_later,
                 bg="#95a5a6", fg="white", font=("Arial", 11),
                 width=10).pack(side="right")
        
        self.log_status(f"Background update check: v{remote_version} available (current: v{self.current_version})")
    
    def handle_startup_farming(self):
        """Handle automatic startup farming if enabled"""
        try:
            if not self.settings.get("start_at_boot", False):
                return
            
            # Parse boot wait time
            boot_wait_str = self.settings.get("boot_wait_time", "4 min")
            if "sec" in boot_wait_str:  # Handle seconds for testing
                wait_seconds = int(boot_wait_str.split()[0])
            else:  # Handle minutes
                wait_minutes = int(boot_wait_str.split()[0])
                wait_seconds = wait_minutes * 60
            
            self.log_status(f"Windows startup detected - will start farming in {boot_wait_str}")
            self.log_status("You can cancel this by clicking 'Stop Hour Farming' before the timer expires")
            
            # Initialize startup progress tracking
            self.startup_total_seconds = wait_seconds
            self.startup_remaining_seconds = wait_seconds
            self.startup_in_progress = True
            
            # Enable the stop button so user can cancel startup
            self.stop_button.config(state="normal")
            
            # Update the status label and start countdown
            self.update_startup_progress()
            
        except Exception as e:
            self.log_status(f"Error in startup farming handler: {e}")
    
    def update_startup_progress(self):
        """Update the startup progress display"""
        try:
            if not hasattr(self, 'startup_in_progress') or not self.startup_in_progress:
                return
            
            # Calculate progress percentage
            elapsed_seconds = self.startup_total_seconds - self.startup_remaining_seconds
            progress_percent = (elapsed_seconds / self.startup_total_seconds) * 100
            
            # Format time remaining
            minutes = self.startup_remaining_seconds // 60
            seconds = self.startup_remaining_seconds % 60
            time_str = f"{minutes:02d}:{seconds:02d}"
            
            # Update status label with progress
            status_text = f"Auto-start in {time_str} ({progress_percent:.0f}%) - Click 'Stop Hour Farming' to cancel"
            self.status_label.config(text=status_text, fg="orange")
            
            # Check if countdown is complete
            if self.startup_remaining_seconds <= 0:
                self.startup_in_progress = False
                # The stop button will be managed by start_afk() when farming actually begins
                self.auto_start_farming()
                return
            
            # Decrement counter and schedule next update
            self.startup_remaining_seconds -= 1
            self.root.after(1000, self.update_startup_progress)  # Update every second
            
        except Exception as e:
            self.log_status(f"Error in startup progress update: {e}")
            self.startup_in_progress = False
    
    def auto_start_farming(self):
        """Automatically start farming (called after boot wait time)"""
        try:
            # Reset startup progress tracking
            self.startup_in_progress = False
            
            # Check if user hasn't manually started already or cancelled
            if self.is_running:
                self.log_status("Farming already running - skipping auto-start")
                self.status_label.config(text="Already running", fg="green")
                return
            
            # Check if startup was cancelled (this check might be redundant but keeps it safe)
            if hasattr(self, 'startup_in_progress') and not getattr(self, 'startup_in_progress', False):
                # This means it was cancelled, don't proceed
                self.stop_button.config(state="disabled")
                return
            
            # Check if we have a selected server
            if not self.selected_server:
                # Try to select the first available server
                filtered_servers = self.get_filtered_servers()
                if filtered_servers:
                    self.selected_server = filtered_servers[0]
                    # Update the selected index for consistency
                    self.settings["selected_server_index"] = 0
                    self.save_settings()
                    self.log_status(f"Auto-selected server: {self.selected_server['name']}")
                else:
                    self.log_status("No servers available for auto-start - please add servers first")
                    self.status_label.config(text="No servers available", fg="red")
                    return
            
            self.log_status("Starting automatic farming due to Windows startup setting...")
            self.status_label.config(text="Auto-starting farming...", fg="green")
            self.start_afk()
            
        except Exception as e:
            self.log_status(f"Error in auto-start farming: {e}")
            self.status_label.config(text="Auto-start failed", fg="red")
    
    def show_server_context_menu(self, event):
        """Show context menu for server list"""
        try:
            # Get the index of the clicked item
            index = self.server_listbox.nearest(event.y)
            if index < 0 or index >= len(self.get_filtered_servers()):
                return
            
            # Select the item
            self.server_listbox.selection_clear(0, tk.END)
            self.server_listbox.selection_set(index)
            
            # Create context menu
            context_menu = tk.Menu(self.root, tearoff=0)
            context_menu.add_command(label="Ping Server", command=lambda: self.ping_selected_server(index))
            context_menu.add_separator()
            context_menu.add_command(label="Remove Server", command=self.remove_server)
            
            # Show menu
            context_menu.tk_popup(event.x_root, event.y_root)
        except Exception as e:
            error_msg = f"Error showing context menu: {e}"
            print(error_msg)
            self.log_status(error_msg)
    
    def get_filtered_servers(self):
        """Get servers based on current filter"""
        if self.server_filter == "premium":
            return [s for s in self.servers if s.get("premium", False)]
        elif self.server_filter == "non_premium":
            return [s for s in self.servers if not s.get("premium", False)]
        else:
            return self.servers
    
    def ping_selected_server(self, listbox_index):
        """Ping the selected server and show result"""
        try:
            filtered_servers = self.get_filtered_servers()
            if listbox_index >= len(filtered_servers):
                return
            
            server = filtered_servers[listbox_index]
            server_name = server.get('name', 'Unknown')
            server_ip = server.get('ip', '')
            
            # Show progress dialog
            progress_dialog = tk.Toplevel(self.root)
            progress_dialog.title("Pinging Server")
            progress_dialog.geometry("300x100")
            progress_dialog.resizable(False, False)
            progress_dialog.transient(self.root)
            progress_dialog.grab_set()
            
            # Center the dialog
            progress_dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
            
            tk.Label(progress_dialog, text=f"Pinging {server_name}...", font=("Arial", 10)).pack(pady=20)
            
            progress_bar = ttk.Progressbar(progress_dialog, mode='indeterminate')
            progress_bar.pack(pady=10, padx=20, fill="x")
            progress_bar.start()
            
            def ping_thread():
                is_online = self.ping_server(server_ip, timeout=10)
                
                progress_dialog.after(0, lambda: progress_bar.stop())
                progress_dialog.after(0, lambda: progress_dialog.destroy())
                
                # Show result
                status = "ONLINE" if is_online else "OFFLINE"
                color = "green" if is_online else "red"
                icon = "info" if is_online else "warning"
                
                messagebox.showinfo("Ping Result", 
                                  f"Server: {server_name}\nIP: {server_ip}\nStatus: {status}",
                                  icon=icon)
                
                self.log_status(f"Pinged {server_name}: {status}")
            
            # Start ping in separate thread
            ping_thread_obj = threading.Thread(target=ping_thread, daemon=True)
            ping_thread_obj.start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to ping server: {e}")
            self.log_status(f"Error pinging server: {e}")
        
    def create_gui(self):
        # Main container with reduced padding
        main_container = tk.Frame(self.root)
        main_container.pack(fill="both", expand=True, padx=3, pady=3)
        
        # Top section - Title and Hours
        top_frame = tk.Frame(main_container)
        top_frame.pack(fill="x", pady=(0, 5))
        
        # Title
        title_label = tk.Label(top_frame, text="Rust Battlemetrics AFK Hour Adder Tool", 
                              font=("Arial", 16, "bold"))
        title_label.pack()
        
        # Hours display
        self.hours_frame = tk.Frame(top_frame)
        self.hours_frame.pack(pady=2)
        
        tk.Label(self.hours_frame, text="Battlemetrics Hours:", font=("Arial", 12)).pack()
        self.hours_label = tk.Label(self.hours_frame, text="00:00:00", 
                                   font=("Arial", 14, "bold"), fg="green")
        self.hours_label.pack()
        
        # Bottom section - Control buttons and status (pack first to ensure it's always visible)
        bottom_frame = tk.Frame(main_container)
        bottom_frame.pack(side="bottom", fill="x", pady=(5, 0))
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill="both", expand=True, pady=(0, 5))
        
        # Tab 1: Server Management
        self.create_server_tab()
        
        # Tab 2: Basic Settings
        self.create_basic_settings_tab()
        
        # Tab 3: Automation Settings
        self.create_automation_tab()
        
        # Tab 4: Server Switching
        self.create_server_switching_tab()
        
        # Tab 5: Server History Builder
        self.create_add_servers_played_tab()
        

        
        # Control Buttons
        control_frame = tk.Frame(bottom_frame)
        control_frame.pack(pady=(0, 5))
        
        self.start_button = tk.Button(control_frame, text="Start Hour Farming", command=self.start_afk, 
                                     bg="green", fg="white", font=("Arial", 12, "bold"))
        self.start_button.pack(side="left", padx=5)
        
        self.stop_button = tk.Button(control_frame, text="Stop Hour Farming", command=self.stop_afk, 
                                    bg="#8B0000", fg="white", font=("Arial", 12, "bold"), state="disabled")
        self.stop_button.pack(side="left", padx=5)
        
        # Reset Settings Button
        tk.Button(control_frame, text="Reset All Settings", 
                 command=self.reset_to_defaults, bg="#FF6B35", fg="white", 
                 font=("Arial", 10, "bold")).pack(side="left", padx=5)
        
        # Kill Rust Button
        tk.Button(control_frame, text="Kill Rust", 
                 command=self.kill_rust, bg="#8B0000", fg="white", 
                 font=("Arial", 10, "bold")).pack(side="left", padx=5)
        
        # Status
        self.status_label = tk.Label(bottom_frame, text="Ready", font=("Arial", 10), fg="blue")
        self.status_label.pack()
        
        # Links and Version
        links_frame = tk.Frame(bottom_frame)
        links_frame.pack(pady=2)
        
        # Create horizontal layout for version and links
        version_links_frame = tk.Frame(links_frame)
        version_links_frame.pack()
        
        github_label = tk.Label(version_links_frame, text="GitHub", font=("Arial", 9), fg="blue", cursor="hand2")
        github_label.pack(side="left", padx=(0, 10))
        
        discord_label = tk.Label(version_links_frame, text="Discord", font=("Arial", 9), fg="blue", cursor="hand2")
        discord_label.pack(side="left")
        
        # Add click handlers for links
        def open_github(event):
            webbrowser.open(f"https://github.com/{self.github_repo}")
        
        def open_discord(event):
            webbrowser.open("https://discord.gg/a5T2xBhKgt")
        
        github_label.bind("<Button-1>", open_github)
        discord_label.bind("<Button-1>", open_discord)
        

        
        self.update_server_list()
        self.update_timer()
        
        # Initialize GUI elements with loaded settings
        self.initialize_gui_with_settings()
        
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
        content_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
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
        
        self.server_listbox = tk.Listbox(listbox_frame, font=("Arial", 9), height=6)
        scrollbar = tk.Scrollbar(listbox_frame, orient="vertical", command=self.server_listbox.yview)
        self.server_listbox.config(yscrollcommand=scrollbar.set)
        
        self.server_listbox.pack(side="left", fill="both", expand=True)
        self.server_listbox.bind('<<ListboxSelect>>', self.on_server_selection_change)
        self.server_listbox.bind('<Button-3>', self.show_server_context_menu)  # Right-click context menu
        scrollbar.pack(side="right", fill="y")
        
        # Right side - Buttons
        right_frame = tk.Frame(content_frame, width=150)
        right_frame.pack(side="right", fill="y")
        right_frame.pack_propagate(False)  # Maintain minimum width
        
        # Server management buttons
        tk.Label(right_frame, text="Server Actions", font=("Arial", 11, "bold")).pack(pady=(0, 10))
        
        tk.Button(right_frame, text="Add Server", command=self.add_server).pack(pady=2, fill="x")
        tk.Button(right_frame, text="Remove Server", command=self.remove_server).pack(pady=2, fill="x")
        
        tk.Button(right_frame, text="Validate Servers", command=self.validate_servers,
                 bg="#2196F3", fg="white").pack(pady=2, fill="x")
        tk.Button(right_frame, text="Delete All Premium", command=self.delete_all_premium, 
                 bg="#8B0000", fg="white").pack(pady=2, fill="x")
        tk.Button(right_frame, text="Delete All Non-Premium", command=self.delete_all_non_premium, 
                 bg="#8B0000", fg="white").pack(pady=2, fill="x")
        
        # Separator
        tk.Frame(right_frame, height=2, bg="gray").pack(fill="x", pady=10)
        
        # Filter buttons
        tk.Label(right_frame, text="Filter Servers", font=("Arial", 11, "bold")).pack(pady=(0, 10))
        
        tk.Button(right_frame, text="Show All", command=self.show_all_servers).pack(pady=2, fill="x")
        tk.Button(right_frame, text="Hide Premium", command=self.hide_premium_servers).pack(pady=2, fill="x")
        tk.Button(right_frame, text="Hide Non-Premium", command=self.hide_non_premium_servers).pack(pady=2, fill="x")
        
        # Separator
        tk.Frame(right_frame, height=2, bg="gray").pack(fill="x", pady=10)
        
        # Server count information
        tk.Label(right_frame, text="Server Statistics", font=("Arial", 11, "bold")).pack(pady=(0, 5))
        
        self.server_count_label = tk.Label(right_frame, text="", font=("Arial", 9), fg="gray", justify="left")
        self.server_count_label.pack(pady=(0, 5), anchor="w")
    
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
        interval_frame = tk.LabelFrame(left_col, text="AFK Loop Settings", padx=5, pady=5)
        interval_frame.pack(fill="x", pady=(0, 10))
        
        pause_frame = tk.Frame(interval_frame)
        pause_frame.pack(fill="x")
        
        self.pause_label = tk.Label(pause_frame, text="Interval:")
        self.pause_label.pack(side="left")
        self.pause_var = tk.StringVar(value="1 min")
        self.pause_dropdown = ttk.Combobox(pause_frame, textvariable=self.pause_var, 
                                          values=["45 sec", "1 min", "2 min", "5 min", "10 min", "15 min", "19 min", "20 min", "25 min"], 
                                          width=12, state="readonly")
        self.pause_dropdown.pack(side="left", padx=10)
        self.pause_dropdown.bind('<<ComboboxSelected>>', lambda e: self.on_pause_change())
        
        # Connection Wait Time Setting
        connection_frame = tk.LabelFrame(left_col, text="Connection Settings", padx=5, pady=5)
        connection_frame.pack(fill="x", pady=(0, 10))
        
        connection_wait_frame = tk.Frame(connection_frame)
        connection_wait_frame.pack(fill="x")
        
        tk.Label(connection_wait_frame, text="Connection wait time:").pack(side="left")
        self.connection_wait_time_var = tk.StringVar(value=self.settings.get("connection_wait_time", "1 min"))
        self.connection_wait_time_dropdown = ttk.Combobox(connection_wait_frame, textvariable=self.connection_wait_time_var, 
                                                         values=["45 sec", "1 min", "1m 30s", "2 min"], 
                                                         width=8, state="readonly")
        self.connection_wait_time_dropdown.pack(side="left", padx=10)
        self.connection_wait_time_dropdown.bind('<<ComboboxSelected>>', lambda e: self.on_dropdown_change("connection_wait_time"))
        
        connection_note = tk.Label(connection_frame, text="Time to wait for server connection to stabilize", 
                                  font=("Arial", 8), wraplength=350)
        connection_note.pack(anchor="w", padx=20, pady=2)
        
        # Kill After Movement Setting
        kill_frame = tk.LabelFrame(left_col, text="Combat Settings", padx=5, pady=5)
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
        system_frame = tk.LabelFrame(right_col, text="System Settings", padx=5, pady=5)
        system_frame.pack(fill="x", pady=(0, 10))
        
        self.enable_disconnect_var = tk.BooleanVar(value=self.settings.get("enable_startup_disconnect", False))
        tk.Checkbutton(system_frame, text="Enable startup disconnect command", 
                      variable=self.enable_disconnect_var, command=self.on_disconnect_change).pack(anchor="w", pady=2)
        
        disconnect_note = tk.Label(system_frame, text="Toggle this on if you're already connected to a server.\nThis will disconnect you and connect to your selected server.", 
                                  font=("Arial", 8), wraplength=350, fg="gray")
        disconnect_note.pack(anchor="w", padx=20, pady=2)
        
        self.disable_beep_var = tk.BooleanVar(value=self.settings.get("disable_beep", True))
        tk.Checkbutton(system_frame, text="Disable beep sounds", 
                      variable=self.disable_beep_var, command=self.on_beep_change).pack(anchor="w", pady=2)
        
        # Update checking settings
        self.auto_check_updates_var = tk.BooleanVar(value=self.settings.get("auto_check_updates", True))
        tk.Checkbutton(system_frame, text="Check for updates on startup", 
                      variable=self.auto_check_updates_var, command=self.on_auto_update_check_change).pack(anchor="w", pady=2)
        
        check_note = tk.Label(system_frame, text="Automatically check for new versions when the program starts", 
                             font=("Arial", 8), wraplength=350, fg="gray")
        check_note.pack(anchor="w", padx=20, pady=(0, 5))
        
        # Auto update settings
        self.auto_update_var = tk.BooleanVar(value=self.settings.get("auto_update", False))
        tk.Checkbutton(system_frame, text="Automatically install updates (no confirmation)", 
                      variable=self.auto_update_var, command=self.on_auto_update_change).pack(anchor="w", pady=2)
        
        install_note = tk.Label(system_frame, text="Download and install updates automatically without showing confirmation dialogs", 
                               font=("Arial", 8), wraplength=350, fg="gray")
        install_note.pack(anchor="w", padx=20, pady=(0, 5))
        
        # Typing mode setting
        typing_mode_frame = tk.Frame(system_frame)
        typing_mode_frame.pack(fill="x", pady=5)
        
        tk.Label(typing_mode_frame, text="Command typing mode:").pack(side="left")
        self.typing_mode_var = tk.StringVar(value=self.settings.get("typing_mode", "human"))
        self.typing_mode_dropdown = ttk.Combobox(typing_mode_frame, textvariable=self.typing_mode_var, 
                                               values=["human", "bot", "kid", "pro"], width=8, state="readonly")
        self.typing_mode_dropdown.pack(side="left", padx=10)
        self.typing_mode_dropdown.bind('<<ComboboxSelected>>', lambda e: self.on_dropdown_change("typing_mode"))
        
        typing_note = tk.Label(system_frame, text="Global setting for ALL commands: Human = realistic typing | Bot = instant paste | Kid = slow with mistakes | Pro = fast ~90 WPM", 
                              font=("Arial", 8), wraplength=350)
        typing_note.pack(anchor="w", padx=20, pady=2)
        
        # Special Modes
        modes_frame = tk.LabelFrame(right_col, text="Special Modes", padx=10, pady=10)
        modes_frame.pack(fill="x")
        
        self.minimal_activity_var = tk.BooleanVar(value=self.settings.get("minimal_activity", False))
        self.minimal_checkbox = tk.Checkbutton(modes_frame, text="Minimal Activity Mode", 
                                              variable=self.minimal_activity_var,
                                              command=self.on_minimal_activity_change)
        self.minimal_checkbox.pack(anchor="w", pady=2)
        
        minimal_note = tk.Label(modes_frame, text="Sets 19min interval + kill after movement", 
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
        
        self.auto_start_rust_var = tk.BooleanVar(value=self.settings.get("auto_start_rust", True))
        tk.Checkbutton(game_frame, text="Auto start Rust and focus window", 
                      variable=self.auto_start_rust_var, command=self.on_auto_start_rust_change).pack(anchor="w", pady=2)
        
        # Rust load time setting
        load_time_frame = tk.Frame(game_frame)
        load_time_frame.pack(fill="x", pady=5)
        
        tk.Label(load_time_frame, text="Rust load time:").pack(side="left")
        self.rust_load_time_var = tk.StringVar(value=self.settings.get("rust_load_time", "1 min"))
        self.rust_load_time_dropdown = ttk.Combobox(load_time_frame, textvariable=self.rust_load_time_var, 
                                                   values=["30 sec", "1 min", "2 min", "3 min", "4 min", "5 min"], 
                                                   width=8, state="readonly")
        self.rust_load_time_dropdown.pack(side="left", padx=10)
        self.rust_load_time_dropdown.bind('<<ComboboxSelected>>', lambda e: self.on_dropdown_change("rust_load_time"))
        
        auto_start_note = tk.Label(game_frame, text="Starts via Steam, waits for load time, then focuses", 
                                  font=("Arial", 8), wraplength=350)
        auto_start_note.pack(anchor="w", padx=20, pady=2)
        
        # Auto Restart
        restart_frame = tk.LabelFrame(left_col, text="Auto Restart", padx=10, pady=10)
        restart_frame.pack(fill="x")
        
        self.auto_restart_game_var = tk.BooleanVar(value=self.settings.get("auto_restart_game", False))
        tk.Checkbutton(restart_frame, text="Auto restart game for game updates", 
                      variable=self.auto_restart_game_var,
                      command=self.on_auto_restart_change).pack(anchor="w", pady=2)
        
        restart_interval_frame = tk.Frame(restart_frame)
        restart_interval_frame.pack(fill="x", pady=5)
        
        self.restart_label = tk.Label(restart_interval_frame, text="Restart every:")
        self.restart_label.pack(side="left")
        self.restart_interval_var = tk.StringVar(value=self.settings.get("restart_interval", "3h"))
        self.restart_dropdown = ttk.Combobox(restart_interval_frame, textvariable=self.restart_interval_var, 
                                           values=["1h", "2h", "3h", "6h", "8h", "12h", "24h"], width=8, state="readonly")
        self.restart_dropdown.pack(side="left", padx=10)
        self.restart_dropdown.bind('<<ComboboxSelected>>', lambda e: self.on_dropdown_change("restart_interval"))
        
        # Right column
        right_col = tk.Frame(content_frame)
        right_col.pack(side="right", fill="both", expand=True)
        
        # Startup Settings
        startup_frame = tk.LabelFrame(right_col, text="Windows Startup", padx=10, pady=10)
        startup_frame.pack(fill="x")
        
        self.start_at_boot_var = tk.BooleanVar(value=self.settings.get("start_at_boot", False))
        tk.Checkbutton(startup_frame, text="Start farming at Windows startup", 
                      variable=self.start_at_boot_var, command=self.on_boot_change).pack(anchor="w", pady=2)
        
        # Boot wait time setting
        boot_wait_frame = tk.Frame(startup_frame)
        boot_wait_frame.pack(fill="x", pady=5)
        
        tk.Label(boot_wait_frame, text="Boot wait time:").pack(side="left")
        self.boot_wait_time_var = tk.StringVar(value=self.settings.get("boot_wait_time", "4 min"))
        self.boot_wait_time_dropdown = ttk.Combobox(boot_wait_frame, textvariable=self.boot_wait_time_var, 
                                                   values=["1 min", "2 min", "3 min", "4 min", "5 min"], 
                                                   width=8, state="readonly")
        self.boot_wait_time_dropdown.pack(side="left", padx=10)
        self.boot_wait_time_dropdown.bind('<<ComboboxSelected>>', lambda e: self.on_dropdown_change("boot_wait_time"))
        
        boot_note = tk.Label(startup_frame, text="App starts immediately but waits selected time before farming", 
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
                      variable=self.switch_enabled_var, command=self.on_server_switching_change).pack(anchor="w")
        
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
        self.time_range_combo.bind('<<ComboboxSelected>>', lambda e: self.on_dropdown_change("time_range"))
        self.time_range_hours_label = tk.Label(time_range_frame, text="hours")
        self.time_range_hours_label.pack(side="left")
        
        # Stealth Mode
        stealth_frame = tk.LabelFrame(left_col, text="Stealth Mode", padx=10, pady=10)
        stealth_frame.pack(fill="x")
        
        self.stealth_mode_var = tk.BooleanVar(value=self.settings["server_switching"].get("stealth_mode", False))
        tk.Checkbutton(stealth_frame, text="Enable Stealth Mode", 
                      variable=self.stealth_mode_var,
                      command=self.on_stealth_mode_change).pack(anchor="w")
        
        stealth_note = tk.Label(stealth_frame, text="5-20min random sessions, minimal activity, no respawn cycles", 
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
        
    def create_add_servers_played_tab(self):
        """Create the server history builder tab"""
        add_servers_frame = ttk.Frame(self.notebook)
        self.notebook.add(add_servers_frame, text="Server History Builder")
        
        # Main content
        content_frame = tk.Frame(add_servers_frame)
        content_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Settings Section
        settings_frame = tk.LabelFrame(content_frame, text="Settings", padx=20, pady=15, font=("Arial", 12, "bold"))
        settings_frame.pack(fill="x", pady=(0, 20))
        settings_frame.config(height=150)  # Set minimum height to ensure all content is visible
        
        # Create two-column layout for settings
        settings_container = tk.Frame(settings_frame)
        settings_container.pack(fill="both", expand=True)
        
        # Left column - Server Selection
        left_settings = tk.Frame(settings_container, width=250, height=120)
        left_settings.pack(side="left", fill="y", padx=(0, 20))
        left_settings.pack_propagate(False)  # Maintain fixed width and height
        
        tk.Label(left_settings, text="Server Selection:", font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 5))
        
        # Server type selection
        self.add_servers_type_var = tk.StringVar(value=self.settings.get("add_servers_type", "all"))
        
        tk.Radiobutton(left_settings, text="All Servers", variable=self.add_servers_type_var, 
                      value="all", font=("Arial", 10), command=self.on_add_servers_type_change).pack(anchor="w", pady=2)
        tk.Radiobutton(left_settings, text="Premium Only", variable=self.add_servers_type_var, 
                      value="premium", font=("Arial", 10), command=self.on_add_servers_type_change).pack(anchor="w", pady=2)
        tk.Radiobutton(left_settings, text="Non-Premium Only", variable=self.add_servers_type_var, 
                      value="non_premium", font=("Arial", 10), command=self.on_add_servers_type_change).pack(anchor="w", pady=2)
        
        # Right column - Connection Settings
        right_settings = tk.Frame(settings_container)
        right_settings.pack(side="left", fill="both", expand=True)
        
        tk.Label(right_settings, text="Connection Settings:", font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 5))
        
        # Connection time setting
        time_frame = tk.Frame(right_settings)
        time_frame.pack(anchor="w", pady=5)
        
        tk.Label(time_frame, text="Time per server:", font=("Arial", 10)).pack(side="left")
        self.add_servers_time_var = tk.StringVar(value=self.settings.get("add_servers_time", "1 min"))
        self.add_servers_time_dropdown = ttk.Combobox(time_frame, textvariable=self.add_servers_time_var, 
                                                     values=["30 sec", "45 sec", "1 min", "1m 30s", "2 min", "3 min", "4 min", "5 min"], 
                                                     width=10, state="readonly")
        self.add_servers_time_dropdown.pack(side="left", padx=(10, 0))
        self.add_servers_time_dropdown.bind('<<ComboboxSelected>>', lambda e: self.on_add_servers_time_change())
        
        # Auto-start setting
        auto_start_frame = tk.Frame(right_settings)
        auto_start_frame.pack(anchor="w", pady=5)
        
        self.add_servers_auto_start_var = tk.BooleanVar(value=self.settings.get("add_servers_auto_start", True))
        tk.Checkbutton(auto_start_frame, text="Auto-start Rust if needed", 
                      variable=self.add_servers_auto_start_var, font=("Arial", 10), command=self.on_add_servers_auto_start_change).pack(side="left")
        
        # Preview Section
        preview_frame = tk.LabelFrame(content_frame, text="Preview", padx=20, pady=15, font=("Arial", 12, "bold"))
        preview_frame.pack(fill="x", pady=(0, 20))
        
        # Preview container with two columns
        preview_container = tk.Frame(preview_frame)
        preview_container.pack(fill="x")
        
        # Left - Server counts
        left_preview = tk.Frame(preview_container)
        left_preview.pack(side="left", fill="both", expand=True)
        
        self.add_servers_preview_label = tk.Label(left_preview, text="", 
                                                font=("Arial", 10), fg="black", justify="left")
        self.add_servers_preview_label.pack(anchor="w")
        
        # Right - Time estimate
        right_preview = tk.Frame(preview_container)
        right_preview.pack(side="right", fill="both", expand=True)
        
        self.add_servers_time_label = tk.Label(right_preview, text="", 
                                             font=("Arial", 10), fg="blue", justify="left")
        self.add_servers_time_label.pack(anchor="w")
        
        # Action Section
        action_frame = tk.LabelFrame(content_frame, text="Action", padx=20, pady=15, font=("Arial", 12, "bold"))
        action_frame.pack(fill="x", pady=(0, 20))
        
        # Button container
        button_container = tk.Frame(action_frame)
        button_container.pack(pady=10)
        
        # Main start button
        self.start_add_servers_btn = tk.Button(button_container, text="Add Servers to Player History", 
                                             command=self.start_add_servers_unified, 
                                             bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), 
                                             width=25, height=1)
        self.start_add_servers_btn.pack(side="left", padx=10)
        
        # Stop button
        self.stop_add_servers_btn = tk.Button(button_container, text="Stop", 
                                            command=self.stop_add_servers, 
                                            bg="#f44336", fg="white", font=("Arial", 10, "bold"), 
                                            width=8, height=1, state="disabled")
        self.stop_add_servers_btn.pack(side="left", padx=10)
        
        # Simple spacing
        tk.Frame(content_frame, height=20).pack()
        
        # Initialize preview
        self.update_add_servers_preview()
        
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
    
    def initialize_gui_with_settings(self):
        """Initialize GUI elements with loaded settings"""
        try:
            # Set pause dropdown based on loaded pause_time
            pause_time = self.settings.get("pause_time", 60)
            if pause_time == 45:
                self.pause_var.set("45 sec")
            elif pause_time == 60:
                self.pause_var.set("1 min")
            elif pause_time == 120:
                self.pause_var.set("2 min")
            elif pause_time == 300:
                self.pause_var.set("5 min")
            elif pause_time == 600:
                self.pause_var.set("10 min")
            elif pause_time == 900:
                self.pause_var.set("15 min")
            elif pause_time == 1140:
                self.pause_var.set("19 min")
            elif pause_time == 1200:
                self.pause_var.set("20 min")
            elif pause_time == 1500:
                self.pause_var.set("25 min")
            else:
                self.pause_var.set("1 min")  # Default fallback
            
            # Initialize checkboxes with loaded settings
            self.kill_after_movement_var.set(self.settings.get("kill_after_movement", False))
            self.enable_disconnect_var.set(self.settings.get("enable_startup_disconnect", False))
            self.disable_beep_var.set(self.settings.get("disable_beep", True))
            self.auto_check_updates_var.set(self.settings.get("auto_check_updates", True))
            self.minimal_activity_var.set(self.settings.get("minimal_activity", False))
            
        except Exception as e:
            self.log_status(f"Error initializing GUI with settings: {e}")
    
    def on_kill_after_movement_change(self):
        """Handle kill after movement checkbox change"""
        status = "ENABLED" if self.kill_after_movement_var.get() else "DISABLED"
        self.log_status(f"Kill after movement: {status}")
        if self.kill_after_movement_var.get():
            # When kill after movement is enabled, set AFK loop to 10 minutes
            self.pause_var.set("10 min")
            self.log_status("AFK loop automatically set to 10 minutes")
        self.save_settings()
    
    def on_stealth_mode_change(self):
        """Handle stealth mode checkbox change"""
        status = "ENABLED" if self.stealth_mode_var.get() else "DISABLED"
        self.log_status(f"Stealth mode: {status}")
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
        self.save_settings()
    
    def on_minimal_activity_change(self):
        """Handle minimal activity checkbox change"""
        status = "ENABLED" if self.minimal_activity_var.get() else "DISABLED"
        self.log_status(f"Minimal Activity Mode: {status}")
        if self.minimal_activity_var.get():
            # Store current values before changing them
            self.previous_pause_value = self.pause_var.get()
            self.previous_kill_value = self.kill_after_movement_var.get()
            
            # When minimal activity is enabled, set AFK loop to 19 minutes and enable kill after movement
            self.pause_var.set("19 min")
            self.kill_after_movement_var.set(True)
            self.log_status("Automatically set: AFK loop to 19 minutes, Kill after movement enabled")
            
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
            self.log_status("Restored previous AFK loop and kill after movement settings")
            
            self.pause_dropdown.config(state="readonly")
            self.pause_label.config(fg="black")
            self.kill_checkbox.config(state="normal")
        self.save_settings()
    
    def on_auto_restart_change(self):
        """Handle auto restart checkbox change"""
        status = "ENABLED" if self.auto_restart_game_var.get() else "DISABLED"
        interval = self.restart_interval_var.get() if self.auto_restart_game_var.get() else "N/A"
        self.log_status(f"Auto restart game for updates: {status} (Interval: {interval})")
        if self.auto_restart_game_var.get():
            # When auto restart is enabled, enable restart interval dropdown
            self.restart_dropdown.config(state="readonly")
            self.restart_label.config(fg="black")
        else:
            # When auto restart is disabled, disable restart interval dropdown
            self.restart_dropdown.config(state="disabled")
            self.restart_label.config(fg="gray")
        self.save_settings()
    
    def on_pause_change(self):
        """Handle pause dropdown change and save settings"""
        try:
            pause_text = self.pause_var.get()
            
            if pause_text == "45 sec":
                pause_seconds = 45
            elif pause_text == "1 min":
                pause_seconds = 60
            elif pause_text == "2 min":
                pause_seconds = 120
            elif pause_text == "5 min":
                pause_seconds = 300
            elif pause_text == "10 min":
                pause_seconds = 600
            elif pause_text == "15 min":
                pause_seconds = 900
            elif pause_text == "19 min":
                pause_seconds = 1140
            elif pause_text == "20 min":
                pause_seconds = 1200
            elif pause_text == "25 min":
                pause_seconds = 1500
            else:
                return  # Invalid selection, don't save
            
            # If kill after movement is enabled, set AFK loop to 10 minutes
            if self.kill_after_movement_var.get():
                pause_seconds = 600
                self.pause_var.set("10 min")
                
            self.settings["pause_time"] = pause_seconds
            self.save_settings()
        except Exception as e:
            self.log_status(f"Error during dropdown change: {e}")
            pass  # Continue despite errors during dropdown change
    
    def on_dropdown_change(self, dropdown_name):
        """Handle dropdown change and save settings"""
        if dropdown_name == "connection_wait_time":
            value = self.connection_wait_time_var.get()
            self.log_status(f"Connection wait time: {value}")
        elif dropdown_name == "typing_mode":
            value = self.typing_mode_var.get()
            self.log_status(f"Command typing mode: {value}")
        elif dropdown_name == "rust_load_time":
            value = self.rust_load_time_var.get()
            self.log_status(f"Rust load time: {value}")
        elif dropdown_name == "restart_interval":
            value = self.restart_interval_var.get()
            self.log_status(f"Auto restart interval: {value}")
        elif dropdown_name == "boot_wait_time":
            value = self.boot_wait_time_var.get()
            self.log_status(f"Boot wait time: {value}")
        elif dropdown_name == "time_range":
            value = self.time_range_var.get()
            self.log_status(f"Server switching time range: {value} hours")
        self.save_settings()
    
    def on_add_servers_time_change(self):
        """Handle add servers time dropdown change"""
        self.log_status(f"Server History Builder time changed to: {self.add_servers_time_var.get()}")
        self.update_add_servers_preview()
        self.save_settings()
    
    def on_add_servers_type_change(self):
        """Handle Server History Builder server type selection change"""
        selection = self.add_servers_type_var.get()
        if selection == "all":
            self.log_status("Server History Builder: All Servers selected")
        elif selection == "premium":
            self.log_status("Server History Builder: Premium Only selected")
        elif selection == "non_premium":
            self.log_status("Server History Builder: Non-Premium Only selected")
        
        self.update_add_servers_preview()
        self.save_settings()
    
    def on_disconnect_change(self):
        """Handle startup disconnect checkbox change"""
        status = "ENABLED" if self.enable_disconnect_var.get() else "DISABLED"
        self.log_status(f"Startup disconnect command: {status}")
        self.save_settings()
    
    def on_beep_change(self):
        """Handle beep sounds checkbox change"""
        status = "DISABLED" if self.disable_beep_var.get() else "ENABLED"
        self.log_status(f"Beep sounds: {status}")
        self.save_settings()
    
    def on_auto_update_check_change(self):
        """Handle auto check updates checkbox change"""
        self.settings["auto_check_updates"] = self.auto_check_updates_var.get()
        status = "ENABLED" if self.auto_check_updates_var.get() else "DISABLED"
        self.log_status(f"Automatic update checking: {status}")
        self.save_settings()
    
    def on_auto_update_change(self):
        """Handle auto update checkbox change"""
        self.settings["auto_update"] = self.auto_update_var.get()
        status = "ENABLED" if self.auto_update_var.get() else "DISABLED"
        self.log_status(f"Automatic updates: {status}")
        self.save_settings()
    
    def on_auto_start_rust_change(self):
        """Handle auto start Rust checkbox change"""
        status = "ENABLED" if self.auto_start_rust_var.get() else "DISABLED"
        load_time = self.rust_load_time_var.get() if self.auto_start_rust_var.get() else "N/A"
        self.log_status(f"Auto start Rust: {status} (Load time: {load_time})")
        self.save_settings()
    
    def on_boot_change(self):
        """Handle start at boot checkbox change"""
        status = "ENABLED" if self.start_at_boot_var.get() else "DISABLED"
        wait_time = self.boot_wait_time_var.get() if self.start_at_boot_var.get() else "N/A"
        self.log_status(f"Start farming at Windows startup: {status} (Wait time: {wait_time})")
        self.save_settings()
    
    def on_server_switching_change(self):
        """Handle server switching checkbox change"""
        status = "ENABLED" if self.switch_enabled_var.get() else "DISABLED"
        time_range = self.time_range_var.get() if self.switch_enabled_var.get() else "N/A"
        self.log_status(f"Auto Server Switching: {status} (Time range: {time_range} hours)")
        self.save_settings()
    
    def on_add_servers_auto_start_change(self):
        """Handle Server History Builder auto-start checkbox change"""
        status = "ENABLED" if self.add_servers_auto_start_var.get() else "DISABLED"
        self.log_status(f"Server History Builder auto-start Rust: {status}")
        self.save_settings()
    
    def on_server_selection_change(self, event):
        """Handle server listbox selection change"""
        selection = self.server_listbox.curselection()
        if selection:
            # Get the displayed servers (considering current filter)
            displayed_servers = self.get_filtered_servers()
            if selection[0] < len(displayed_servers):
                selected_server = displayed_servers[selection[0]]
                # Find the actual index in the full server list
                actual_index = self.servers.index(selected_server)
                self.settings["selected_server_index"] = actual_index
                
                premium_text = " (Premium)" if selected_server.get("premium", False) else ""
                self.log_status(f"Selected server: {selected_server['name']}{premium_text}")
                self.save_settings()
    
    def restore_server_selection(self):
        """Restore the previously selected server"""
        try:
            saved_index = self.settings.get("selected_server_index", 0)
            if 0 <= saved_index < len(self.servers):
                selected_server = self.servers[saved_index]
                
                # Find this server in the current filtered display
                displayed_servers = self.get_filtered_servers()
                for display_index, server in enumerate(displayed_servers):
                    if server == selected_server:
                        self.server_listbox.selection_set(display_index)
                        self.server_listbox.see(display_index)
                        break
        except Exception as e:
            self.log_status(f"Error during selection restoration: {e}")
            pass  # Continue despite errors during selection restoration
    
    def save_settings(self):
        settings_file = os.path.join(self.data_folder, "settings.json")
        try:
            # Update settings from GUI
            self.settings["kill_after_movement"] = self.kill_after_movement_var.get()
            self.settings["enable_startup_disconnect"] = self.enable_disconnect_var.get()
            self.settings["disable_beep"] = self.disable_beep_var.get()
            self.settings["auto_check_updates"] = self.auto_check_updates_var.get()
            self.settings["minimal_activity"] = self.minimal_activity_var.get()
            self.settings["auto_start_rust"] = self.auto_start_rust_var.get()
            self.settings["rust_load_time"] = self.rust_load_time_var.get()
            self.settings["connection_wait_time"] = self.connection_wait_time_var.get()
            self.settings["start_at_boot"] = self.start_at_boot_var.get()
            self.settings["boot_wait_time"] = self.boot_wait_time_var.get()
            self.settings["auto_restart_game"] = self.auto_restart_game_var.get()
            self.settings["restart_interval"] = self.restart_interval_var.get()
            self.settings["typing_mode"] = self.typing_mode_var.get()
            self.settings["add_servers_auto_start"] = self.add_servers_auto_start_var.get()
            self.settings["add_servers_time"] = self.add_servers_time_var.get()
            self.settings["add_servers_type"] = self.add_servers_type_var.get()
            # Note: selected_server_index is saved directly in on_server_selection_change()
            self.settings["server_switching"]["enabled"] = self.switch_enabled_var.get()
            self.settings["server_switching"]["time_range"] = self.time_range_var.get()
            self.settings["server_switching"]["stealth_mode"] = self.stealth_mode_var.get()
            
            # Don't log here - let individual handlers log specific changes
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
                              "• Disable initial startup disconnect command\n" +
                              "• Enable beep sounds\n" +
                              "• Disable auto server switching\n" +
                              "• Disable stealth mode\n" +
                              "• Clear server rotation selection\n\n" +
                              "This action cannot be undone!"):
            
            # Reset settings to defaults
            self.settings = {
                "pause_time": 60,  # 1 minute in seconds
                "kill_after_movement": False,
                "enable_startup_disconnect": False,
                "disable_beep": True,
                "minimal_activity": False,
                "auto_start_rust": True,
                "rust_load_time": "1 min",
                "connection_wait_time": "1 min",
                "start_at_boot": False,
                "boot_wait_time": "4 min",
                "auto_restart_game": False,
                "restart_interval": "3h",
                "add_servers_auto_start": True,
                "add_servers_time": "1 min",
                "add_servers_type": "all",
                "selected_server_index": 0,
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
            self.enable_disconnect_var.set(False)
            self.disable_beep_var.set(True)
            self.auto_check_updates_var.set(True)
            self.minimal_activity_var.set(False)
            self.auto_start_rust_var.set(True)
            self.rust_load_time_var.set("1 min")
            self.connection_wait_time_var.set("1 min")
            self.start_at_boot_var.set(False)
            self.boot_wait_time_var.set("4 min")
            self.auto_restart_game_var.set(False)
            self.restart_interval_var.set("3h")
            self.add_servers_auto_start_var.set(True)
            self.add_servers_time_var.set("1 min")
            self.add_servers_type_var.set("all")
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
    
    def kill_rust(self):
        """Kill all Rust processes"""
        try:
            import psutil
            killed_processes = 0
            
            # Find and kill all Rust processes
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and 'rust' in proc.info['name'].lower():
                        proc.terminate()
                        killed_processes += 1
                        self.log_status(f"Terminated Rust process: {proc.info['name']} (PID: {proc.info['pid']})")
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            if killed_processes > 0:
                self.log_status(f"Successfully killed {killed_processes} Rust process(es)")
            else:
                self.log_status("No Rust processes found running")
                
        except ImportError:
            self.log_status("Error: psutil module not available for killing processes")
        except Exception as e:
            self.log_status(f"Error killing Rust processes: {e}")
    
    def log_status(self, message):
        """Log status messages to file and print to console"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        
        # Always print to console first
        print(log_message)
        
        # Try to write to log file with multiple fallback attempts
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                # Ensure data directory exists
                os.makedirs(self.data_folder, exist_ok=True)
                
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(log_message + "\n")
                    f.flush()  # Ensure data is written immediately
                break  # Success, exit retry loop
                
            except Exception as e:
                if attempt == max_attempts - 1:  # Last attempt
                    print(f"CRITICAL: Failed to write to log file after {max_attempts} attempts: {e}")
                    print(f"Log file path: {self.log_file}")
                    # Try to create a backup log in current directory
                    try:
                        backup_log = "emergency_log.txt"
                        with open(backup_log, "a", encoding="utf-8") as f:
                            f.write(f"[EMERGENCY LOG] {log_message}\n")
                            f.write(f"[EMERGENCY LOG] Original log file error: {e}\n")
                        print(f"Emergency log created: {backup_log}")
                    except Exception as backup_error:
                        print(f"Could not create emergency log: {backup_error}")
                else:
                    # Wait a bit before retrying
                    import time
                    time.sleep(0.1)
    

    
    def update_server_list(self):
        self.server_listbox.delete(0, tk.END)
        for i, server in enumerate(self.servers):
            # Apply filter
            if self.server_filter == "premium" and not server.get("premium", False):
                continue
            elif self.server_filter == "non_premium" and server.get("premium", False):
                continue
            
            # Build display text with enhanced information
            display_parts = []
            
            # Server name
            display_parts.append(server['name'])
            
            # Status indicators
            indicators = []
            if server.get("premium", False):
                indicators.append("Premium")
            if server.get("official", False):
                indicators.append("Official")
            if server.get("modded", False):
                indicators.append("Modded")
            if server.get("pve", False):
                indicators.append("PvE")
            
            if indicators:
                display_parts.append(f"({', '.join(indicators)})")
            
            # Player count if available
            if server.get("current_players") is not None and server.get("max_players"):
                display_parts.append(f"[{server['current_players']}/{server['max_players']}]")
            
            # Rank if available
            if server.get("rank"):
                display_parts.append(f"Rank #{server['rank']}")
            
            # Country if available
            if server.get("country"):
                display_parts.append(f"({server['country']})")
            
            display_text = " ".join(display_parts)
            self.server_listbox.insert(tk.END, display_text)
        
        # Restore previous server selection if it exists
        self.restore_server_selection()
        
        # Update server count information
        self.update_server_count()
        # Update add servers preview if the tab exists
        if hasattr(self, 'add_servers_preview_label'):
            self.update_add_servers_preview()
    
    def update_server_count(self):
        """Update the server count statistics display"""
        total_servers = len(self.servers)
        premium_servers = len([s for s in self.servers if s.get("premium", False)])
        official_servers = len([s for s in self.servers if s.get("official", False)])
        non_premium_servers = total_servers - premium_servers
        
        count_text = f"Total: {total_servers}\nPremium: {premium_servers}\nOfficial: {official_servers}\nNon-Premium: {non_premium_servers}"
        self.server_count_label.config(text=count_text)
    
    def add_server(self):
        dialog = ServerDialog(self.root)
        if dialog.result:
            self.servers.append(dialog.result)
            self.update_server_list()
            self.save_servers()
            self.log_status(f"Added server: {dialog.result['name']} ({dialog.result['ip']})")
            # Update add servers preview if the tab exists
            if hasattr(self, 'add_servers_preview_label'):
                self.update_add_servers_preview()
    
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
                # Update add servers preview if the tab exists
                if hasattr(self, 'add_servers_preview_label'):
                    self.update_add_servers_preview()
    
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
            # Update add servers preview if the tab exists
            if hasattr(self, 'add_servers_preview_label'):
                self.update_add_servers_preview()
    
    def delete_all_non_premium(self):
        """Delete all non-premium servers"""
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete ALL non-premium servers?\n\nThis action cannot be undone!"):
            non_premium_count = sum(1 for server in self.servers if not server["premium"])
            self.servers = [server for server in self.servers if server["premium"]]
            self.update_server_list()
            self.save_servers()
            self.log_status(f"Deleted {non_premium_count} non-premium servers")
            messagebox.showinfo("Success", f"Deleted {non_premium_count} non-premium servers")
            # Update add servers preview if the tab exists
            if hasattr(self, 'add_servers_preview_label'):
                self.update_add_servers_preview()
    
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
        # Check if server adding is in progress
        if self.is_adding_servers:
            messagebox.showwarning("Warning", "Cannot start hour farming while adding servers to history. Please stop the server adding process first.")
            return
        
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
            elif pause_text == "19 min":
                pause_minutes = 19
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
        except Exception as e:
            error_msg = f"Invalid AFK loop interval: {e}"
            self.log_status(error_msg)
            messagebox.showerror("Error", error_msg)
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
            # Pick random server from rotation
            server_index = random.choice(self.settings["server_switching"]["selected_servers"])
            self.selected_server = self.servers[server_index]
            self.setup_next_server_switch()
            self.log_status(f"Auto server switching enabled - randomly selected: {self.selected_server['name']}")
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
        
        # Set running state and UI before any automation
        self.is_running = True
        self.start_time = datetime.now()
        self.current_server_start_time = datetime.now()
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        
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
                    if not self.is_running:
                        self.log_status("Hour farming stopped by user during Rust startup countdown")
                        return
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
                        progress = int((i / load_time_seconds) * 100)
                        self.status_label.config(text=f"Waiting for Rust to load... {progress}% ({remaining}s remaining)")
                        self.root.update()
                        
                        # Log progress every 10 seconds or at key milestones
                        if i % 10 == 0 or progress in [25, 50, 75]:
                            self.log_status(f"AUTOMATION: Rust loading progress: {progress}% ({remaining}s remaining)")
                        
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
                self.log_status("AUTOMATION: Rust already running, waiting 5 seconds before focusing...")
                # 5-second countdown before focusing window
                for i in range(5, 0, -1):
                    if not self.is_running:
                        self.log_status("Hour farming stopped by user during window focus countdown")
                        return
                    self.status_label.config(text=f"Rust already running - Focusing window in {i} seconds...")
                    self.root.update()
                    time.sleep(1)
                
                self.log_status("AUTOMATION: Now focusing Rust window...")
                self.status_label.config(text="Focusing Rust window...")
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
        
        # Start countdown (state already set above)
        
        self.log_status("=== RUST HOUR ADDER INITIALIZATION ===")
        self.log_status(f"Session started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log_status(f"Target server: {self.selected_server['name']}")
        self.log_status(f"Server IP: {self.selected_server['ip']}")
        self.log_status(f"Premium server: {'Yes' if self.selected_server.get('premium', False) else 'No'}")
        self.log_status(f"Cycle interval: {pause_minutes} minutes ({pause_minutes * 60} seconds)")
        self.log_status(f"Kill after movement: {'ENABLED' if self.kill_after_movement_var.get() else 'DISABLED'}")
        self.log_status(f"Initial startup disconnect: {'ENABLED' if self.enable_disconnect_var.get() else 'DISABLED'}")
        
        if self.switch_enabled_var.get():
            rotation_count = len(self.settings["server_switching"]["selected_servers"])
            self.log_status(f"Auto server switching: ENABLED")
            self.log_status(f"   Servers in rotation: {rotation_count}")
            if self.settings["server_switching"]["stealth_mode"]:
                self.log_status(f"   Switch interval: 5-20 minutes random (STEALTH MODE)")
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
            # Stealth mode: Switch after random 5-20 minutes for better stealth
            stealth_minutes = random.randint(5, 20)
            self.next_server_switch_time = self.current_server_start_time + timedelta(minutes=stealth_minutes)
            
            self.log_status(f"NEXT SERVER SWITCH SCHEDULED (STEALTH MODE):")
            self.log_status(f"   Time: {self.next_server_switch_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.log_status(f"   Duration: {stealth_minutes} minutes from now (randomized 5-20min)")
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
        try:
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
            self.type_command("client.disconnect")
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
            
        except Exception as e:
            error_msg = f"Error during server switching: {e}"
            self.log_status(error_msg)
            # Try to setup next switch anyway to prevent getting stuck
            try:
                self.setup_next_server_switch()
            except Exception as setup_error:
                self.log_status(f"Error setting up next server switch: {setup_error}")
    
    def countdown_and_start(self):
        self.log_status("=== STARTING COUNTDOWN SEQUENCE ===")
        countdown_start = datetime.now()
        
        # Countdown from 3
        for i in range(3, 0, -1):
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
        pause_time = self.settings['pause_time']
        if pause_time < 60:
            self.log_status(f"Cycle Interval: {pause_time} seconds")
        else:
            self.log_status(f"Cycle Interval: {pause_time // 60} minutes {pause_time % 60} seconds" if pause_time % 60 > 0 else f"Cycle Interval: {pause_time // 60} minutes")
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
                
                # Step 1: Initial startup disconnect (ONLY ONCE at the very beginning)
                # This should ONLY happen once when the script first starts, not every cycle
                if not self.initial_disconnect_done and self.settings.get("enable_startup_disconnect", False):
                    step_start = datetime.now()
                    self.log_status("STEP 1: Disconnecting from current server")
                    self.log_status("   Opening console (F1 key)")
                    pyautogui.press('f1')
                    time.sleep(1)
                    
                    self.log_status("   Typing command: 'client.disconnect'")
                    self.type_command("client.disconnect")
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
                    self.initial_disconnect_done = True  # Mark that we've done the initial disconnect
                else:
                    if not self.initial_disconnect_done:
                        self.log_status("STEP 1 SKIPPED: Initial startup disconnect disabled in settings")
                        self.initial_disconnect_done = True  # Mark as done even if skipped
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
                self.type_command(connect_command)
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
                self.type_command("respawn")
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
                    self.type_command("kill")
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
        
        # Step 1: Initial startup disconnect (ONLY ONCE at the very beginning)
        if not self.initial_disconnect_done and self.settings.get("enable_startup_disconnect", False):
            step_start = datetime.now()
            self.log_status("STEALTH STEP 1: Disconnecting from current server")
            self.log_status("   Opening console (F1 key)")
            pyautogui.press('f1')
            time.sleep(1)
            
            self.log_status("   Typing command: 'client.disconnect'")
            self.type_command("client.disconnect")
            self.log_status("   Pressing Enter to execute disconnect")
            pyautogui.press('enter')
            time.sleep(0.5)
            
            self.log_status("   Closing console (F1 key)")
            pyautogui.press('f1')
            self.log_status("   Waiting 5 seconds for disconnect to complete...")
            time.sleep(5)
            
            step_duration = (datetime.now() - step_start).total_seconds()
            self.log_status(f"STEALTH STEP 1 COMPLETED in {step_duration:.1f}s - Server disconnection finished")
            self.initial_disconnect_done = True  # Mark that we've done the initial disconnect
        else:
            if not self.initial_disconnect_done:
                self.log_status("STEALTH STEP 1 SKIPPED: Initial startup disconnect disabled in settings")
                self.initial_disconnect_done = True  # Mark as done even if skipped
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
        self.type_command(connect_command)
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
        self.type_command("kill")
        time.sleep(1)  # Wait after typing
        self.log_status("   Pressing Enter to execute kill command")
        pyautogui.press('enter')
        time.sleep(1)  # Wait after pressing enter
        
        self.log_status("   Closing console (F1 key)")
        pyautogui.press('f1')
        time.sleep(1)  # Wait after closing console
        
        step_duration = (datetime.now() - step_start).total_seconds()
        self.log_status(f"STEALTH STEP 4 COMPLETED in {step_duration:.1f}s - Player eliminated for stealth mode")
        
        self.log_status("=== STEALTH MODE: Now waiting for server switch time (randomized 5-20min) ===")
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
        """Focus the Rust game window using aggressive methods"""
        self.log_status("AUTOMATION: Attempting to focus Rust window...")
        
        # Method 1: Aggressive Windows API approach
        try:
            import ctypes
            from ctypes import wintypes
            
            self.log_status("METHOD 1: Using aggressive Windows API...")
            
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            
            # Find Rust process and window
            import psutil
            rust_hwnd = None
            
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and 'RustClient.exe' in proc.info['name']:
                    pid = proc.info['pid']
                    self.log_status(f"Found RustClient.exe process (PID: {pid})")
                    
                    # Find window belonging to this process
                    def enum_windows_proc(hwnd, lParam):
                        nonlocal rust_hwnd
                        if user32.IsWindowVisible(hwnd):
                            window_pid = wintypes.DWORD()
                            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
                            if window_pid.value == pid:
                                # Get window title to verify it's the main window
                                title_length = user32.GetWindowTextLengthW(hwnd)
                                if title_length > 0:
                                    title_buffer = ctypes.create_unicode_buffer(title_length + 1)
                                    user32.GetWindowTextW(hwnd, title_buffer, title_length + 1)
                                    title = title_buffer.value
                                    self.log_status(f"Found window: '{title}' (HWND: {hwnd})")
                                    rust_hwnd = hwnd
                                    return False  # Stop enumeration
                        return True
                    
                    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
                    user32.EnumWindows(EnumWindowsProc(enum_windows_proc), 0)
                    
                    if rust_hwnd:
                        break
            
            if rust_hwnd:
                self.log_status("METHOD 1: Attempting aggressive window focusing...")
                
                # Multiple aggressive focusing techniques
                # 1. Restore window if minimized
                user32.ShowWindow(rust_hwnd, 9)  # SW_RESTORE
                time.sleep(0.1)
                
                # 2. Bring to front
                user32.BringWindowToTop(rust_hwnd)
                time.sleep(0.1)
                
                # 3. Set as foreground window
                user32.SetForegroundWindow(rust_hwnd)
                time.sleep(0.1)
                
                # 4. Activate window
                user32.SetActiveWindow(rust_hwnd)
                time.sleep(0.1)
                
                # 5. Force focus with keyboard input
                user32.SetFocus(rust_hwnd)
                
                self.log_status("SUCCESS: Applied aggressive focusing to Rust window")
                return True
            else:
                self.log_status("METHOD 1: Could not find Rust window handle")
                
        except Exception as e:
            self.log_status(f"METHOD 1: Error - {e}")
        
        # Method 2: pygetwindow with aggressive activation
        try:
            import pygetwindow as gw
            
            self.log_status("METHOD 2: pygetwindow with aggressive activation...")
            
            possible_titles = ["Rust", "RustClient", "Rust Client", "RustClient.exe"]
            
            for title in possible_titles:
                try:
                    windows = gw.getWindowsWithTitle(title)
                    if windows:
                        window = windows[0]
                        self.log_status(f"Found window: '{title}'")
                        
                        # Multiple activation attempts
                        window.restore()  # Restore if minimized
                        time.sleep(0.1)
                        window.activate()  # Activate
                        time.sleep(0.1)
                        window.maximize()  # Try maximize
                        time.sleep(0.1)
                        window.activate()  # Activate again
                        
                        self.log_status(f"SUCCESS: Aggressively activated window '{title}'")
                        return True
                except Exception as e:
                    self.log_status(f"Failed to activate '{title}': {e}")
                    continue
            
            # Try partial matches with aggressive activation
            all_windows = gw.getAllWindows()
            for window in all_windows:
                if window.title and any(keyword.lower() in window.title.lower() for keyword in ["rust", "client"]):
                    try:
                        self.log_status(f"Trying partial match: '{window.title}'")
                        window.restore()
                        time.sleep(0.1)
                        window.activate()
                        time.sleep(0.1)
                        window.activate()  # Double activate
                        self.log_status(f"SUCCESS: Activated '{window.title}'")
                        return True
                    except Exception as e:
                        self.log_status(f"Error activating window '{window.title}': {e}")
                        continue
            
            self.log_status("METHOD 2: No suitable windows found")
            
        except ImportError:
            if install_package("pygetwindow==0.0.9"):
                return self.focus_rust_window()
            else:
                self.log_status("METHOD 2: Failed to install pygetwindow")
        except Exception as e:
            self.log_status(f"METHOD 2: Error - {e}")
        
        # Method 3: Keyboard simulation to force focus
        try:
            self.log_status("METHOD 3: Using keyboard simulation...")
            
            # Alt+Tab to cycle through windows
            pyautogui.hotkey('alt', 'tab')
            time.sleep(0.5)
            
            # Try multiple Alt+Tab presses to find Rust
            for i in range(5):  # Try up to 5 windows
                pyautogui.press('tab')
                time.sleep(0.3)
                # Could check window title here, but for now just cycle
            
            pyautogui.press('enter')  # Select current window
            time.sleep(0.2)
            
            self.log_status("METHOD 3: Completed Alt+Tab cycling")
            return True
            
        except Exception as e:
            self.log_status(f"METHOD 3: Error - {e}")
        
        # Method 4: Click on taskbar (if visible)
        try:
            self.log_status("METHOD 4: Attempting taskbar click...")
            
            # This is a last resort - click somewhere on the taskbar area where Rust might be
            # Get screen dimensions
            import pyautogui
            screen_width, screen_height = pyautogui.size()
            
            # Click in taskbar area (bottom of screen)
            taskbar_y = screen_height - 40
            
            # Try clicking in several taskbar positions
            for x_offset in [200, 400, 600, 800]:
                if x_offset < screen_width:
                    try:
                        pyautogui.click(x_offset, taskbar_y)
                        time.sleep(0.2)
                    except Exception as e:
                        self.log_status(f"Error clicking taskbar button: {e}")
                        continue
            
            self.log_status("METHOD 4: Attempted taskbar clicks")
            return True
            
        except Exception as e:
            self.log_status(f"METHOD 4: Error - {e}")
        
        self.log_status("WARNING: All focusing methods completed - you may need to manually tab to Rust")
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
        """Type text with realistic human-like timing and patterns"""
        typing_start = datetime.now()
        char_count = len(text)
        
        # Human typing characteristics
        base_wpm = random.uniform(35, 55)  # Random typing speed between 35-55 WPM
        base_delay = 60 / (base_wpm * 5)  # Convert WPM to seconds per character
        
        # Track typing rhythm - humans have bursts and slowdowns
        rhythm_momentum = 1.0
        last_char_time = time.time()
        
        for i, char in enumerate(text):
            if not self.is_running and not self.is_adding_servers:
                self.log_status(f"WARNING: Typing interrupted at character {i+1}/{char_count}")
                return
            
            # Character-specific delays (realistic human patterns)
            char_delay = base_delay
            
            # Slower on certain characters
            if char in 'qzxQZX':  # Uncommon letters
                char_delay *= random.uniform(1.3, 1.8)
            elif char in '1234567890!@#$%^&*()':  # Numbers and symbols
                char_delay *= random.uniform(1.2, 1.6)
            elif char in ' ':  # Space - often faster
                char_delay *= random.uniform(0.7, 1.0)
            elif char.isupper():  # Capital letters (shift key)
                char_delay *= random.uniform(1.1, 1.4)
            
            # Word boundaries - slight pause at spaces and punctuation
            if char in ' .,;:!?':
                char_delay *= random.uniform(1.2, 1.8)
            
            # Typing rhythm variations
            current_time = time.time()
            time_since_last = current_time - last_char_time
            
            # If typing too fast, slow down (fatigue)
            if time_since_last < base_delay * 0.5:
                rhythm_momentum *= 0.95
            # If typing slow, speed up (getting into rhythm)
            elif time_since_last > base_delay * 2:
                rhythm_momentum *= 1.05
            
            # Keep momentum in reasonable bounds
            rhythm_momentum = max(0.7, min(1.4, rhythm_momentum))
            char_delay *= rhythm_momentum
            
            # Add natural randomness (±30%)
            char_delay *= random.uniform(0.7, 1.3)
            
            # Occasional longer pauses (thinking/hesitation)
            if random.random() < 0.08:  # 8% chance
                thinking_pause = random.uniform(0.3, 1.2)
                time.sleep(thinking_pause)
            
            # Very rare typos that get immediately corrected (2% chance)
            if random.random() < 0.02 and char.isalpha():
                # Type wrong character
                nearby_keys = {
                    'a': 'sq', 's': 'adw', 'd': 'sfre', 'f': 'dgrt', 'g': 'fhty',
                    'h': 'gjyu', 'j': 'hkui', 'k': 'jlio', 'l': 'kop',
                    'q': 'wa', 'w': 'qes', 'e': 'wrd', 'r': 'etf', 't': 'ryg',
                    'y': 'tuh', 'u': 'yij', 'i': 'uok', 'o': 'ipl', 'p': 'ol',
                    'z': 'x', 'x': 'zc', 'c': 'xv', 'v': 'cb', 'b': 'vn',
                    'n': 'bm', 'm': 'n'
                }
                
                wrong_chars = nearby_keys.get(char.lower(), 'qwerty')
                wrong_char = random.choice(wrong_chars)
                if char.isupper():
                    wrong_char = wrong_char.upper()
                
                pyautogui.write(wrong_char)
                time.sleep(random.uniform(0.1, 0.3))  # Brief pause before correction
                pyautogui.press('backspace')
                time.sleep(random.uniform(0.05, 0.15))
            
            # Type the actual character
            pyautogui.write(char)
            time.sleep(char_delay)
            last_char_time = time.time()
        
        typing_duration = (datetime.now() - typing_start).total_seconds()
        avg_char_time = typing_duration / char_count if char_count > 0 else 0
        actual_wpm = (char_count / 5) / (typing_duration / 60) if typing_duration > 0 else 0
        self.log_status(f"   Human typed '{text}' ({char_count} chars in {typing_duration:.2f}s, ~{actual_wpm:.0f} WPM)")
    
    def kid_type(self, text):
        """Type text like a kid - slow with occasional mistakes and backspaces"""
        typing_start = datetime.now()
        char_count = len(text)
        typed_chars = 0
        mistakes_made = 0
        
        i = 0
        while i < len(text):
            if not self.is_running and not self.is_adding_servers:
                self.log_status(f"WARNING: Typing interrupted at character {i+1}/{char_count}")
                return
            
            char = text[i]
            
            # 15% chance of making a mistake
            if random.random() < 0.15 and char.isalpha():
                # Make a mistake - type a random nearby key
                mistake_chars = 'qwertyuiopasdfghjklzxcvbnm'
                mistake_char = random.choice(mistake_chars)
                pyautogui.write(mistake_char)
                typed_chars += 1
                mistakes_made += 1
                
                # Pause as kid realizes mistake (0.3-0.8 seconds)
                mistake_pause = random.uniform(0.3, 0.8)
                time.sleep(mistake_pause)
                
                # Backspace to fix mistake
                pyautogui.press('backspace')
                time.sleep(random.uniform(0.1, 0.3))
            
            # Type the correct character
            pyautogui.write(char)
            typed_chars += 1
            
            # Kid typing speed: 15-25 WPM (slower than human)
            # Average 20 WPM = 100 chars/min = 1.67 chars/sec = 0.6 sec/char
            # Add randomness: 0.4-0.9 seconds per character
            delay = random.uniform(0.4, 0.9)
            time.sleep(delay)
            
            i += 1
        
        typing_duration = (datetime.now() - typing_start).total_seconds()
        avg_char_time = typing_duration / typed_chars if typed_chars > 0 else 0
        wpm = (typed_chars / 5) / (typing_duration / 60) if typing_duration > 0 else 0
        self.log_status(f"   Kid typed '{text}' ({typed_chars} chars, {mistakes_made} mistakes, {typing_duration:.2f}s, ~{wpm:.0f} WPM)")
    
    def pro_type(self, text):
        """Type text like a pro - fast ~90 WPM with consistent rhythm"""
        typing_start = datetime.now()
        char_count = len(text)
        
        for i, char in enumerate(text):
            if not self.is_running and not self.is_adding_servers:
                self.log_status(f"WARNING: Typing interrupted at character {i+1}/{char_count}")
                return
            
            pyautogui.write(char)
            
            # Pro typing speed: ~90 WPM
            # 90 WPM = 450 chars/min = 7.5 chars/sec = 0.133 sec/char
            # Add slight randomness for realism: 0.11-0.16 seconds per character
            delay = random.uniform(0.11, 0.16)
            time.sleep(delay)
        
        typing_duration = (datetime.now() - typing_start).total_seconds()
        avg_char_time = typing_duration / char_count if char_count > 0 else 0
        wpm = (char_count / 5) / (typing_duration / 60) if typing_duration > 0 else 0
        self.log_status(f"   Pro typed '{text}' ({char_count} chars in {typing_duration:.2f}s, ~{wpm:.0f} WPM)")
    
    def type_command(self, text):
        """Type command based on global typing mode setting"""
        try:
            typing_mode = self.settings.get("typing_mode", "human")
            
            if typing_mode == "bot":
                # Bot mode: Instant paste
                pyautogui.write(text)
                self.log_status(f"   Pasted '{text}' (bot mode)")
            elif typing_mode == "kid":
                # Kid mode: Slow with mistakes
                self.kid_type(text)
            elif typing_mode == "pro":
                # Pro mode: Fast ~90 WPM
                self.pro_type(text)
            else:
                # Human mode: Realistic typing (default)
                typing_start = datetime.now()
                char_count = len(text)
                
                for i, char in enumerate(text):
                    # Check if any active process should be stopped
                    if not self.is_running and not self.is_adding_servers:
                        self.log_status(f"WARNING: Typing interrupted at character {i+1}/{char_count}")
                        return
                    
                    pyautogui.write(char)
                    # Random delay between 0.05 and 0.15 seconds for human-like typing
                    delay = 0.05 + (time.time() % 0.1)
                    time.sleep(delay)
                
                typing_duration = (datetime.now() - typing_start).total_seconds()
                avg_char_time = typing_duration / char_count if char_count > 0 else 0
                self.log_status(f"   Typed '{text}' ({char_count} chars in {typing_duration:.2f}s, avg: {avg_char_time:.3f}s/char)")
                
        except Exception as e:
            error_msg = f"Error typing command '{text}': {e}"
            self.log_status(error_msg)
    
    def stop_afk(self, play_beep=True):
        stop_time = datetime.now()
        self.is_running = False
        
        # Cancel startup countdown if it's in progress
        if hasattr(self, 'startup_in_progress') and self.startup_in_progress:
            self.startup_in_progress = False
            self.log_status("Windows startup auto-farming cancelled by user")
            self.status_label.config(text="Startup auto-farming cancelled", fg="red")
            # Disable stop button since countdown is cancelled
            self.stop_button.config(state="disabled")
            # Reset status after a few seconds
            self.root.after(3000, lambda: self.status_label.config(text="Ready", fg="blue"))
            return
        
        # Also stop server adding if it's running
        if self.is_adding_servers:
            self.stop_add_servers()
        
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
    
    def start_add_all_servers(self):
        """Start adding all servers to history (legacy method)"""
        # Set the new interface to match this selection
        if hasattr(self, 'add_servers_type_var'):
            self.add_servers_type_var.set("all")
            self.update_add_servers_preview()
        
        if self.is_running:
            self.log_status("Cannot add servers while hour farming is running. Please stop farming first.")
            return
        
        if not self.servers:
            self.log_status("No servers available. Please add some servers first.")
            return
        
        self.current_add_servers_list = self.servers.copy()
        # Randomize the server order for more natural patterns
        random.shuffle(self.current_add_servers_list)
        self.log_status(f"Randomized server order for natural connection pattern")
        self.start_add_servers_process("all servers")
    
    def start_add_premium_servers(self):
        """Start adding premium servers to history (legacy method)"""
        # Set the new interface to match this selection
        if hasattr(self, 'add_servers_type_var'):
            self.add_servers_type_var.set("premium")
            self.update_add_servers_preview()
        
        if self.is_running:
            self.log_status("Cannot add servers while hour farming is running. Please stop farming first.")
            return
        
        premium_servers = [server for server in self.servers if server.get("premium", False)]
        if not premium_servers:
            self.log_status("No premium servers available.")
            return
        
        self.current_add_servers_list = premium_servers
        # Randomize the server order for more natural patterns
        random.shuffle(self.current_add_servers_list)
        self.log_status(f"Randomized server order for natural connection pattern")
        self.start_add_servers_process("premium servers")
    
    def start_add_non_premium_servers(self):
        """Start adding non-premium servers to history (legacy method)"""
        # Set the new interface to match this selection
        if hasattr(self, 'add_servers_type_var'):
            self.add_servers_type_var.set("non_premium")
            self.update_add_servers_preview()
        
        if self.is_running:
            self.log_status("Cannot add servers while hour farming is running. Please stop farming first.")
            return
        
        non_premium_servers = [server for server in self.servers if not server.get("premium", False)]
        if not non_premium_servers:
            self.log_status("No non-premium servers available.")
            return
        
        self.current_add_servers_list = non_premium_servers
        # Randomize the server order for more natural patterns
        random.shuffle(self.current_add_servers_list)
        self.log_status(f"Randomized server order for natural connection pattern")
        self.start_add_servers_process("non-premium servers")
    
    def start_add_servers_process(self, server_type):
        """Start the server adding process"""
        # Confirm with user
        server_count = len(self.current_add_servers_list)
        connection_time = self.add_servers_time_var.get()
        
        # Calculate breakdown for confirmation
        premium_count = len([s for s in self.current_add_servers_list if s.get("premium", False)])
        non_premium_count = server_count - premium_count
        
        # Only show manual instruction if auto-start is disabled
        auto_start_enabled = self.add_servers_auto_start_var.get()
        
        # Create detailed confirmation message
        breakdown_text = ""
        if server_type == "all servers":
            breakdown_text = f"• Premium servers: {premium_count}\n• Non-premium servers: {non_premium_count}\n"
        elif server_type == "premium servers":
            breakdown_text = f"• All {premium_count} servers are premium\n"
        elif server_type == "non-premium servers":
            breakdown_text = f"• All {non_premium_count} servers are non-premium\n"
        
        # Log the process details instead of showing popup
        total_time = self.calculate_total_time(server_count, connection_time)
        self.log_status(f"Starting to add {server_count} {server_type} for {connection_time} each")
        self.log_status(f"Breakdown: {breakdown_text.strip()}")
        self.log_status(f"Total estimated time: {total_time}")
        
        if not auto_start_enabled:
            self.log_status("Make sure Rust is running and you're in the main menu")
        
        # Start countdown before beginning the process
        self.start_add_servers_countdown(server_count, server_type, connection_time)
    
    def calculate_total_time(self, server_count, connection_time):
        """Calculate total estimated time for adding servers"""
        time_mapping = {
            "30 sec": 30,
            "45 sec": 45,
            "1 min": 60,
            "1m 30s": 90,
            "2 min": 120,
            "3 min": 180,
            "4 min": 240,
            "5 min": 300
        }
        
        seconds_per_server = time_mapping.get(connection_time, 60)
        total_seconds = server_count * (seconds_per_server + 10)  # Add 10 seconds for connection overhead
        
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{int(hours)}h {int(minutes)}m"
        else:
            return f"{int(minutes)}m {int(seconds)}s"
    
    def start_add_servers_countdown(self, server_count, server_type, connection_time):
        """Start countdown before beginning the add servers process"""
        self.is_adding_servers = True
        self.current_add_server_index = 0
        
        # Update UI - disable buttons
        if hasattr(self, 'add_all_servers_btn'):
            # Legacy buttons (if they exist)
            self.add_all_servers_btn.config(state="disabled")
            self.add_premium_servers_btn.config(state="disabled")
            self.add_non_premium_servers_btn.config(state="disabled")
        
        if hasattr(self, 'start_add_servers_btn'):
            # New unified interface
            self.start_add_servers_btn.config(state="disabled")
        
        self.stop_add_servers_btn.config(state="normal")
        
        # Start countdown in a separate thread
        countdown_thread = threading.Thread(target=self.countdown_worker, 
                                           args=(server_count, server_type, connection_time), 
                                           daemon=True)
        countdown_thread.start()
    
    def countdown_worker(self, server_count, server_type, connection_time):
        """Worker thread for countdown"""
        try:
            # 5-second countdown - update button text
            for i in range(5, 0, -1):
                if not self.is_adding_servers:  # Check if user stopped the process
                    return
                self.start_add_servers_btn.config(text=f"Starting... {i}")
                time.sleep(1)
            
            if not self.is_adding_servers:  # Final check before starting
                return
                
            # Update button to show process is running
            self.start_add_servers_btn.config(text="Adding Servers...")
            
            # Log the start
            self.log_status(f"=== STARTED ADDING {server_count} {server_type.upper()} TO HISTORY ===")
            self.log_status(f"Connection time per server: {connection_time}")
            
            # Start the actual process
            self.add_servers_thread = threading.Thread(target=self.add_servers_worker, daemon=True)
            self.add_servers_thread.start()
            
        except Exception as e:
            self.log_status(f"Error during countdown: {e}")
            self.stop_add_servers()
    
    def update_add_servers_stats(self):
        """Update the server statistics display in the Server History Builder tab (legacy method)"""
        # This method is kept for compatibility but the new interface uses update_add_servers_preview
        if hasattr(self, 'add_servers_preview_label'):
            self.update_add_servers_preview()
    
    def update_add_servers_preview(self):
        """Update the preview display in the Server History Builder tab"""
        if not hasattr(self, 'add_servers_preview_label'):
            return
            
        total_servers = len(self.servers)
        premium_servers = len([s for s in self.servers if s.get("premium", False)])
        non_premium_servers = total_servers - premium_servers
        
        # Get selected server type
        server_type = self.add_servers_type_var.get()
        connection_time = self.add_servers_time_var.get()
        
        # Calculate what will be processed
        if server_type == "all":
            selected_count = total_servers
            selected_premium = premium_servers
            selected_non_premium = non_premium_servers
            type_text = "All Servers"
        elif server_type == "premium":
            selected_count = premium_servers
            selected_premium = premium_servers
            selected_non_premium = 0
            type_text = "Premium Servers Only"
        else:  # non_premium
            selected_count = non_premium_servers
            selected_premium = 0
            selected_non_premium = non_premium_servers
            type_text = "Non-Premium Only"
        
        # Left side - What will be processed
        if selected_count == 0:
            preview_text = f"WARNING: No servers available for '{type_text}'"
            self.add_servers_preview_label.config(text=preview_text, fg="red")
            self.start_add_servers_btn.config(state="disabled")
        else:
            preview_text = f"Will process: {selected_count} servers\n"
            if server_type == "all":
                preview_text += f"• {selected_premium} Premium\n• {selected_non_premium} Non-Premium"
            elif server_type == "premium":
                preview_text += f"• All {selected_premium} are Premium"
            else:
                preview_text += f"• All {selected_non_premium} are Non-Premium"
            
            self.add_servers_preview_label.config(text=preview_text, fg="black")
            self.start_add_servers_btn.config(state="normal")
        
        # Right side - Time estimate
        if selected_count > 0:
            estimated_time = self.calculate_total_time(selected_count, connection_time)
            time_text = f"Estimated time: {estimated_time}\n"
            time_text += f"Connection time: {connection_time} per server"
            self.add_servers_time_label.config(text=time_text)
        else:
            self.add_servers_time_label.config(text="No servers to process")
    
    def start_add_servers_unified(self):
        """Unified method to start adding servers based on current settings"""
        if self.is_running:
            self.log_status("Cannot add servers while hour farming is running. Please stop farming first.")
            return
        
        # Get current settings
        server_type = self.add_servers_type_var.get()
        
        # Prepare server list based on selection
        if server_type == "all":
            self.current_add_servers_list = self.servers.copy()
            server_type_text = "all servers"
        elif server_type == "premium":
            self.current_add_servers_list = [server for server in self.servers if server.get("premium", False)]
            server_type_text = "premium servers"
        else:  # non_premium
            self.current_add_servers_list = [server for server in self.servers if not server.get("premium", False)]
            server_type_text = "non-premium servers"
        
        if not self.current_add_servers_list:
            self.log_status(f"No {server_type_text} available.")
            return
        
        # Randomize the server order for more natural patterns
        random.shuffle(self.current_add_servers_list)
        self.log_status(f"Randomized server order for natural connection pattern")
        
        # Start the process
        self.start_add_servers_process(server_type_text)
    
    def add_servers_worker(self):
        """Worker thread for adding servers to history"""
        try:
            # Initial 5-second wait (standard startup delay)
            self.log_status("=== STARTING SERVER HISTORY BUILDER ===")
            self.log_status("Initial startup delay (5 seconds)...")
            for i in range(5):
                if not self.is_adding_servers:
                    return
                time.sleep(1)
            
            connection_time_str = self.add_servers_time_var.get()
            time_mapping = {
                "30 sec": 30,
                "45 sec": 45,
                "1 min": 60,
                "1m 30s": 90,
                "2 min": 120,
                "3 min": 180,
                "4 min": 240,
                "5 min": 300
            }
            connection_time = time_mapping.get(connection_time_str, 60)
            
            # Check auto-start settings and handle Rust startup
            if self.add_servers_auto_start_var.get():
                self.log_status("Auto-start enabled: Checking if Rust needs to be started...")
                if not self.is_rust_running():
                    self.log_status("Rust not detected, starting via Steam...")
                    if self.start_rust_via_steam():
                        # Wait for Rust to load
                        load_time_str = self.rust_load_time_var.get()
                        load_time_mapping = {
                            "30 sec": 30,
                            "1 min": 60,
                            "2 min": 120,
                            "3 min": 180,
                            "4 min": 240,
                            "5 min": 300
                        }
                        load_time = load_time_mapping.get(load_time_str, 60)
                        
                        self.log_status(f"Waiting {load_time_str} for Rust to load...")
                        for second in range(load_time):
                            if not self.is_adding_servers:
                                return
                            
                            progress = int((second / load_time) * 100)
                            remaining = load_time - second
                            
                            # Log progress every 10 seconds or at key milestones
                            if second % 10 == 0 or progress in [25, 50, 75]:
                                self.log_status(f"Rust loading progress: {progress}% ({remaining}s remaining)")
                            
                            time.sleep(1)
                        
                        self.log_status("Focusing Rust window...")
                        self.focus_rust_window()
                        time.sleep(2)  # Extra delay after focusing
                    else:
                        self.log_status("WARNING: Failed to start Rust via Steam")
                        return
                else:
                    self.log_status("Rust is already running, focusing window...")
                    self.focus_rust_window()
                    time.sleep(2)
            else:
                self.log_status("Auto-start disabled: Assuming Rust is already running")
                time.sleep(1)
            
            # Begin server connection loop
            self.log_status(f"Starting to add {len(self.current_add_servers_list)} servers to history...")
            
            for i, server in enumerate(self.current_add_servers_list):
                if not self.is_adding_servers:
                    break
                
                self.current_add_server_index = i
                server_name = server['name']
                server_ip = server['ip']
                
                # Update progress with server type info
                server_type_text = " (Premium)" if server.get("premium", False) else " (Non-Premium)"
                
                self.log_status(f"ADDING SERVER {i+1}/{len(self.current_add_servers_list)}: {server_name}")
                self.log_status(f"   IP: {server_ip}")
                
                # Step 1: Connect to server
                self.log_status("   Opening console (F1 key)")
                pyautogui.press('f1')
                time.sleep(1)  # Wait for console to open
                
                connect_command = f"client.connect {server_ip}"
                self.log_status(f"   Typing command: '{connect_command}'")
                self.type_command(connect_command)
                time.sleep(0.5)
                
                self.log_status("   Pressing Enter to execute connect")
                pyautogui.press('enter')
                time.sleep(1)
                
                # Close console
                self.log_status("   Closing console (F1 key)")
                pyautogui.press('f1')
                time.sleep(1)  # Wait for console to close
                
                # Step 2: Wait for connection time (server registration period)
                self.log_status(f"   Waiting {connection_time_str} for server to register in history...")
                for second in range(connection_time):
                    if not self.is_adding_servers:
                        break
                    time.sleep(1)
                    remaining = connection_time - second - 1
                
                if not self.is_adding_servers:
                    break
                
                # Step 3: Disconnect from server
                self.log_status("   Disconnecting from server")
                pyautogui.press('f1')
                time.sleep(1)  # Wait for console to open
                
                self.log_status("   Typing command: 'client.disconnect'")
                self.type_command("client.disconnect")
                self.log_status("   Pressing Enter to execute disconnect")
                pyautogui.press('enter')
                time.sleep(0.5)
                
                # Close console
                self.log_status("   Closing console (F1 key)")
                pyautogui.press('f1')
                self.log_status("   Waiting 5 seconds for disconnect to complete...")
                time.sleep(5)
                
                self.log_status(f"   Successfully added {server_name} to server history")
                
                # Delay between servers (allow disconnect to complete)
                if i < len(self.current_add_servers_list) - 1:
                    self.log_status("   Waiting 3 seconds before next server...")
                    time.sleep(3)
            
            # Process completed
            if self.is_adding_servers:
                # Calculate statistics for completed servers
                completed_servers = len(self.current_add_servers_list)
                premium_count = len([s for s in self.current_add_servers_list if s.get("premium", False)])
                non_premium_count = completed_servers - premium_count
                
                self.log_status(f"=== COMPLETED ADDING {completed_servers} SERVERS TO HISTORY ===")
                self.log_status(f"Premium servers added: {premium_count}")
                self.log_status(f"Non-premium servers added: {non_premium_count}")
                
                self.log_status(f"SUCCESS: Added {completed_servers} servers ({premium_count} premium, {non_premium_count} non-premium)")
            else:
                self.log_status("=== SERVER ADDING STOPPED BY USER ===")
            
        except Exception as e:
            self.log_status(f"ERROR in server adding: {e}")
        finally:
            # Reset UI state
            self.is_adding_servers = False
            
            if hasattr(self, 'add_all_servers_btn'):
                # Legacy buttons (if they exist)
                self.add_all_servers_btn.config(state="normal")
                self.add_premium_servers_btn.config(state="normal")
                self.add_non_premium_servers_btn.config(state="normal")
            
            if hasattr(self, 'start_add_servers_btn'):
                # New unified interface
                self.start_add_servers_btn.config(state="normal")
            
            self.stop_add_servers_btn.config(state="disabled")
    
    def stop_add_servers(self):
        """Stop the server adding process"""
        self.is_adding_servers = False
        self.log_status("Stopping server adding process...")
        
        if self.add_servers_thread and self.add_servers_thread.is_alive():
            self.add_servers_thread.join(timeout=2)
        
        # Reset UI
        if hasattr(self, 'add_all_servers_btn'):
            # Legacy buttons (if they exist)
            self.add_all_servers_btn.config(state="normal")
            self.add_premium_servers_btn.config(state="normal")
            self.add_non_premium_servers_btn.config(state="normal")
        
        if hasattr(self, 'start_add_servers_btn'):
            # New unified interface
            self.start_add_servers_btn.config(state="normal", text="Add Servers to Player History")
        
        self.stop_add_servers_btn.config(state="disabled")
    

    
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
        self.dialog.geometry("600x500")
        self.dialog.resizable(True, True)
        self.dialog.minsize(500, 400)
        self.dialog.grab_set()
        self.dialog.transient(parent)
        
        tk.Label(self.dialog, text="Select servers to include in rotation:", 
                font=("Arial", 12, "bold")).pack(pady=10)
        
        # Server list with checkboxes
        self.server_vars = []
        server_frame = tk.Frame(self.dialog)
        server_frame.pack(fill="both", expand=True, padx=20, pady=(10, 0))
        
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
        
        # Buttons - use pack with side="bottom" to ensure they stay at bottom
        button_frame = tk.Frame(self.dialog)
        button_frame.pack(side="bottom", fill="x", pady=20, padx=20)
        
        # Action buttons (bottom row) - most important buttons first
        action_frame = tk.Frame(button_frame)
        action_frame.pack(side="bottom", pady=(10, 0))
        
        ok_btn = tk.Button(action_frame, text="OK", command=self.save_selection, 
                          bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=10)
        ok_btn.pack(side="left", padx=10)
        
        cancel_btn = tk.Button(action_frame, text="Cancel", command=self.dialog.destroy,
                              bg="#f44336", fg="white", font=("Arial", 10, "bold"), width=10)
        cancel_btn.pack(side="left", padx=10)
        
        # Bind keyboard shortcuts
        self.dialog.bind('<Return>', lambda e: self.save_selection())
        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())
        
        # Set focus to OK button
        ok_btn.focus_set()
        
        # Quick selection buttons (top row)
        quick_frame = tk.Frame(button_frame)
        quick_frame.pack(side="bottom", pady=(0, 10))
        
        tk.Button(quick_frame, text="Select All", command=self.select_all, width=12).pack(side="left", padx=5)
        tk.Button(quick_frame, text="Clear All", command=self.clear_all, width=12).pack(side="left", padx=5)
        tk.Button(quick_frame, text="Premium Only", command=self.select_premium_only, width=12).pack(side="left", padx=5)
        tk.Button(quick_frame, text="Non-Premium Only", command=self.select_non_premium_only, width=16).pack(side="left", padx=5)
    
    def select_all(self):
        for var in self.server_vars:
            var.set(True)
    
    def clear_all(self):
        for var in self.server_vars:
            var.set(False)
    
    def select_premium_only(self):
        for i, var in enumerate(self.server_vars):
            if i < len(self.servers):
                is_premium = self.servers[i].get("premium", False)
                var.set(is_premium)
    
    def select_non_premium_only(self):
        for i, var in enumerate(self.server_vars):
            if i < len(self.servers):
                is_premium = self.servers[i].get("premium", False)
                var.set(not is_premium)
    
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
        error_msg = f"Error starting application: {e}"
        print(error_msg)
        
        # Try to log the startup error to file
        try:
            import os
            from datetime import datetime
            log_file = os.path.join("data", "afk_log.txt")
            os.makedirs("data", exist_ok=True)
            with open(log_file, "a", encoding="utf-8") as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] CRITICAL ERROR: {error_msg}\n")
        except Exception as log_error:
            print(f"Could not write error to log file: {log_error}")
        
        input("Press Enter to exit...")