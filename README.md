# Xtream Codes M3U Playlist Generator

A Python CLI script designed to reliably retrieve live stream data via the Xtream Codes API and generate clean, standardized M3U/M3U8 playlists. Perfect for automated operation (e.g., via Cron jobs) on Linux systems with advanced system maintenance and playlist optimization features.

## ✨ Features

- **Playlist Generation**: Dynamically creates M3U, M3U8, or M3U8-Plus playlists
- **Multi-Server Support**: Process multiple configured Xtream servers and user accounts in a single run
- **Modular Execution**: All maintenance and cleanup functions are controlled via optional arguments
- **Clear Logging**: Provides timestamped output directly to console (Stdout/Stderr) for easy monitoring

## 🚀 Installation & Prerequisites

### 1. Python Packages

Install the required Python libraries:

```bash
pip install -r requirements.txt
```

### 2. Configuration

Edit the `SERVERS` list directly at the beginning of the Python file to input your credentials:

```python
# --- MULTI-SERVER CONFIGURATION ---
SERVERS = [
    {
        "ID": 1,
        "HOST_URL": "http://portalurl.com",
        "USERNAME": "your_username",
        "PASSWORD": "your_password",
    },
    # Add more server entries here
]
# --- END CONFIGURATION ---
```

## 💡 Usage & Arguments

The script is executed via the command line with optional flags to enable desired features:

| Option | Action | Description | Requires sudo |
|--------|--------|-------------|---------------|
| `--m3u` | File Format | Generates a .m3u file | No |
| `--m3u8_plus` | File Format | Generates a .m3u8_plus file (with extended attributes) | No |
| `--clean` | Cleanup | Cleans stream names (removes API tags, control characters, etc.) | No |
| `--dns` | System Maintenance | Updates the /etc/hosts file with the current host IPs | Yes |
| `--chmod` | File Permissions | Sets the permissions of the generated playlist file to 777 | Yes |

### Example Commands

#### 1. Standard Generation (M3U Default)
Generates the playlists with default settings, no DNS update or cleaning:

```bash
python3 get_services.py
```

#### 2. Full Maintenance with M3U8 Plus
Performs all maintenance steps, including DNS update and cleaning, and generates an M3U8 Plus file (typical for a Cron job):

```bash
sudo python3 get_services.py --m3u8_plus --dns --clean --chmod
```

#### 3. Clean and M3U Generation Only
Generates a cleaned M3U file without making any system changes:

```bash
python3 get_services.py --m3u --clean
```

## 🔒 Important Permission Notes

⚠️ **Root Privileges Required**: The arguments `--dns` (modifying /etc/hosts) and `--chmod` (modifying file permissions in /opt/) require root privileges. The script must be run using `sudo` when these flags are included.

If you run the script without sudo, ensure you omit these flags to prevent execution errors.

## 🔧 System Requirements

- Python 3.x
- Linux operating system (for full functionality)
- Root access (for DNS and chmod operations)

## 📝 Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚡ Automation Setup

For automated execution via Cron, add a line like this to your crontab:

```bash
# Run every 6 hours with full maintenance
0 */6 * * * sudo /usr/bin/python3 /path/to/get_services.py --m3u8_plus --dns --clean --chmod
```

## 🆘 Support

If you encounter any issues or have questions, please open an issue on GitHub.
