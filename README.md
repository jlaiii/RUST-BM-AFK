# Rust Battlemetrics AFK Hour Adder Tool

A Python-based automation tool for Rust players to accumulate hours on Battlemetrics while AFK. This tool provides a user-friendly GUI interface with advanced features for server management, automation, and stealth modes.

## Features

### Core Functionality
- **AFK Hour Farming**: Automatically performs minimal actions to stay connected and accumulate Battlemetrics hours
- **Customizable Intervals**: Set AFK loop intervals from 1-25 minutes
- **Kill After Movement**: Optional feature to prevent spectating after death
- **Auto-disconnect Prevention**: Keeps you connected to servers

### User Interface
- **Tabbed GUI**: Clean, organized interface with multiple tabs for different settings
- **Real-time Status**: Live hour counter and status updates
- **Server Management**: Built-in server browser and management system
- **Settings Persistence**: All settings are automatically saved

### Server Management
- **Multi-server Support**: Add unlimited Rust servers with IP addresses
- **Server Filtering**: Filter between premium and non-premium servers
- **Battlemetrics Integration**: Direct links to browse servers
- **Server Rotation**: Automatically switch between selected servers

### Automation Features
- **Auto Game Launch**: Automatically start Rust via Steam
- **Auto Restart**: Periodic game restarts for updates
- **Windows Startup**: Option to start farming at system boot
- **Stealth Mode**: Minimal activity mode for reduced detection risk

### Advanced Settings
- **Minimal Activity Mode**: 25-minute intervals with kill-after-movement
- **Server Switching**: Rotate between servers every 1-12 hours
- **Sound Controls**: Enable/disable notification beeps
- **Combat Settings**: Configurable kill-after-movement behavior

## Installation

### Prerequisites
- Python 3.7 or higher
- Windows operating system
- Rust game installed via Steam

### Quick Start
1. Download the `rust_battlemetrics_hour_adder.py` file
2. Run the script - it will automatically install required dependencies:
   ```bash
   python rust_battlemetrics_hour_adder.py
   ```

### Manual Installation
If automatic installation fails, install dependencies manually:
```bash
pip install keyboard==0.13.5 pyautogui==0.9.54
```

## Usage

### Basic Setup
1. **Launch the tool**: Run the Python script
2. **Add servers**: Go to "Server Management" tab and add your favorite Rust servers
3. **Configure settings**: Adjust AFK intervals and other preferences in "Basic Settings"
4. **Start farming**: Click "Start Hour Farming" to begin

### Server Management
- **Add Server**: Enter server name and IP address (format: `ip:port`)
- **Remove Server**: Select a server from the list and click remove
- **Filter Servers**: Show/hide premium or non-premium servers
- **Browse Servers**: Direct link to Battlemetrics for server discovery

### Automation Setup
1. **Auto Start Rust**: Enable to automatically launch Rust via Steam
2. **Auto Restart**: Set periodic restarts (1-24 hours) for game updates
3. **Windows Startup**: Enable to start farming when Windows boots
4. **Server Switching**: Configure automatic server rotation

### Stealth Mode
For reduced detection risk:
1. Enable "Server Switching" in the Server Switching tab
2. Check "Enable Stealth Mode"
3. Select servers for rotation
4. The tool will use 25-minute sessions with minimal activity

## Configuration Files

The tool creates a `data/` folder with configuration files:
- `settings.json`: All user preferences and settings
- `servers.json`: Server list with IP addresses and premium status
- `afk_log_YYYYMMDD.txt`: Daily activity logs

## Hotkeys

- **F9**: Emergency stop - immediately stops the farming process
- **Mouse Movement**: Failsafe disabled to prevent accidental stops

## Safety Features

- **Emergency Stop**: F9 key for immediate shutdown
- **Status Logging**: Detailed logs of all activities
- **Settings Backup**: Automatic saving of all configurations
- **Error Handling**: Graceful handling of connection issues

## Troubleshooting

### Common Issues
1. **Dependencies not installing**: Run `pip install keyboard pyautogui` manually
2. **Rust not launching**: Ensure Steam is running and Rust is in your library
3. **Server connection fails**: Verify server IP addresses are correct
4. **Tool not responding**: Use F9 emergency stop and restart
