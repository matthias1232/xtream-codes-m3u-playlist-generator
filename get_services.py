import requests
import time
import re
import logging
import socket
import os
import dns.resolver
import argparse

# --- MULTI-SERVER CONFIGURATION ---
SERVERS = [
    {
        "ID": 1,
        "HOST_URL": "http://portalurl.com",
        "USERNAME": "your_username",
        "PASSWORD": "your_password",
    },
    {
        "ID": 2,
        "HOST_URL": "http://portalurl.com",
        "USERNAME": "your_username",
        "PASSWORD": "your_password",
    },
    # Add more server entries here
]
# --- END CONFIGURATION ---


# Global Static Settings
M3U_BASE_PATH = "/opt/xtream_playlist_" # Will be extended with the ID and file extension
HOSTS_PATH = "/etc/hosts"

# Logging: Configured to log DIRECTLY to the console (stdout/stderr)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Header camouflage for API calls
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/117.0.0.0 Safari/537.36"
}


# --- HOSTS MANAGEMENT FUNCTIONS ---

def get_host_ips(domain):
    """Resolves all current IPv4 addresses ONLY via the system's DNS server."""
    ips = set()
    try:
        # hosts file-independent resolution
        answers = dns.resolver.resolve(domain, 'A')
        for rdata in answers:
            ips.add(rdata.address)
        return list(ips)
    except Exception as e:
        logging.error(f"[ERROR] DNS resolution for {domain} failed: {e}. Using socket fallback.")
        # Fallback (might read hosts file)
        try:
            addrinfo = socket.getaddrinfo(domain, 80, socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
            for result in addrinfo:
                ips.add(result[4][0])
            return list(ips)
        except socket.gaierror:
            return []


def update_etc_hosts(ips, alias):
    """Updates the /etc/hosts file: Deletes old entries for this alias, adds new ones."""
    # CAUTION: Requires root permissions (sudo)!
    try:
        if not os.path.exists(HOSTS_PATH): return

        # Alias format is the domain, e.g., cf.hi-max.me
        
        with open(HOSTS_PATH, 'r') as f:
            lines = f.readlines()

        new_lines = []
        
        # 1. Remove old, uncommented entries for the ALIAS
        for line in lines:
            line_stripped = line.strip()
            # The alias is the domain (e.g., cf.hi-max.me)
            if alias in line_stripped and not line_stripped.startswith('#'):
                logging.info(f"[INFO] Removing old {alias} entry: {line_stripped}")
                continue
            new_lines.append(line)

        # 2. Add new entries
        if ips:
            new_entry_header = f"\n# Added by xtream_m3u script for alias {alias}\n"
            new_lines.append(new_entry_header)
            for ip in ips:
                new_line = f"{ip}\t{alias}\n"
                new_lines.append(new_line)

        # Rewrite the hosts file
        with open(HOSTS_PATH, 'w') as f:
            f.writelines(new_lines)
            
        logging.info(f"[INFO] {HOSTS_PATH} successfully updated with {len(ips)} IPs for {alias}.")

    except Exception as e:
        logging.error(f"[ERROR] Error writing to {HOSTS_PATH}. Requires root permissions! Error: {e}")


# --- STREAM/M3U FUNCTIONS ---

def clean_name(name, do_clean):
    """Cleans up the stream name, only if do_clean is True."""
    
    if not do_clean:
        return name
        
    # Performs cleaning if --clean was used
    
    # Removes unwanted tags like ^tag|1234
    name = re.sub(r"\^[a-zA-Z\|\d]+", "", name) 
    # Removes non-printable characters
    name = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', name) 
    # Collapses multiple spaces
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def fetch_live_streams(host_url, username, password):
    """Fetches the list of live streams from the specific server."""
    url = f"{host_url}/player_api.php?username={username}&password={password}&action=get_live_streams"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8' 
        return response.json()
        
    except Exception as e:
        logging.error(f"[ERROR] API access to {host_url} failed: {e}")
        return []
        
def generate_m3u(streams, host_url, username, password, m3u_path, set_chmod=False, do_clean=False, m3u_type='m3u'):
    """Generates the M3U file based on the requested type and optionally sets permissions."""
    
    # The playlist URL uses the hostname (e.g., http://cf.hi-max.me/user/pass)
    playlist_url_base = f"{host_url}/{username}/{password}"
    
    try:
        seen_names = set()
        
        # 1. Write M3U file (with dynamic path)
        with open(m3u_path, "w", encoding="utf-8") as f: 
            
            # Write header based on type
            if m3u_type in ['m3u8', 'm3u8_plus', 'm3u']:
                f.write("#EXTM3U\n")
            
            for stream in streams:
                raw_name = stream.get("name", "Unknown")
                
                # Conditional cleaning applied here
                name = clean_name(raw_name, do_clean)
                
                # Skip invalid or placeholder names
                if not name or re.match(r"^#+$|^-$|^=+$", name): continue
                # Skip duplicates
                if name in seen_names: continue 
                seen_names.add(name)

                # Collect attributes for EXTINF line
                attributes = []
                
                # Add default attribute
                if stream.get("tv_archive") == 1:
                    name += " [Catch-up]"
                    
                # Add optional attributes for M3U8 Plus / M3U8 standard compatibility
                if m3u_type in ['m3u8', 'm3u8_plus']:
                    stream_id = stream.get("stream_id")
                    
                    # Add standard M3U attributes for better compatibility
                    attributes.append(f'tvg-id="{stream.get("stream_id", "")}"')
                    attributes.append(f'tvg-logo="{stream.get("stream_icon", "")}"')
                    attributes.append(f'group-title="{stream.get("category_name", "")}"')
                
                # Format EXTINF line
                extinf_line = f"#EXTINF:-1 {' '.join(attributes)},{name}\n"
                f.write(extinf_line)
                
                # Write URL line
                stream_id = stream.get("stream_id")
                if stream_id:
                    play_url = f"{playlist_url_base}/{stream_id}" 
                    f.write(f"{play_url}\n")
                    
        logging.info(f"[INFO] {m3u_type.upper()} file {os.path.basename(m3u_path)} written with {len(seen_names)} entries.")
        
        # 2. Set permissions (chmod 777) - only if set_chmod is True
        if set_chmod:
            os.chmod(m3u_path, 0o777) 
            logging.info(f"[INFO] Permissions for {m3u_path} set to 777.")
        else:
            logging.info(f"[INFO] Skipping permissions change (chmod) for {m3u_path}.")


    except Exception as e:
        logging.error(f"[ERROR] Error writing/setting permissions for the M3U: {e}")


# --- MAIN PROGRAM ---

def main():
    # Create Argument Parser
    parser = argparse.ArgumentParser(description="Script to generate cleaned playlists with optional hosts file update, chmod, and name cleaning.")
    
    # Mutually Exclusive Group for M3U type
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--m3u8', action='store_true', help='Generates .m3u8 file (default is .m3u).')
    group.add_argument('--m3u8_plus', action='store_true', help='Generates .m3u8_plus file.')
    
    # Other Optional Arguments
    parser.add_argument('--dns', action='store_true', help='Executes DNS resolution and hosts file update.')
    parser.add_argument('--chmod', action='store_true', help='Executes chmod 777 on the generated M3U files.')
    parser.add_argument('--clean', action='store_true', help='Cleans up the stream names (removes tags, special chars).')
    
    args = parser.parse_args()
    
    # Determine file extension and type
    file_ext = ".m3u"
    m3u_type = "m3u"
    if args.m3u8_plus:
        file_ext = ".m3u8_plus"
        m3u_type = "m3u8_plus"
    elif args.m3u8:
        file_ext = ".m3u8"
        m3u_type = "m3u8"

    
    # Cron mode: Executes all servers sequentially in one run
    
    for server in SERVERS:
        # Extract server-specific configuration
        server_id = server["ID"]
        host_url = server["HOST_URL"]
        username = server["USERNAME"]
        password = server["PASSWORD"]
        
        # Extract hostname (domain)
        host_domain = re.sub(r"^https?://", "", host_url)
        
        # Path for the M3U (using the determined file extension)
        m3u_path = f"{M3U_BASE_PATH}{server_id:02d}{file_ext}"
        
        logging.info(f"--- [SERVER {server_id:02d}] Starting processing for {host_domain} ({m3u_type.upper()}) ---")
        
        # Log the state of optional arguments at the start of processing for this server
        logging.info(f"[CONFIG] Clean Name (--clean): {'Enabled' if args.clean else 'Disabled'}") # NEW LOG LINE
        logging.info(f"[CONFIG] DNS/Hosts Update (--dns): {'Enabled' if args.dns else 'Disabled'}")
        logging.info(f"[CONFIG] File Chmod (--chmod): {'Enabled' if args.chmod else 'Disabled'}")

        
        # 1. Hosts Update Logic (Optional, requires --dns)
        if args.dns: 
            current_ips = get_host_ips(host_domain)
            if current_ips:
                update_etc_hosts(current_ips, host_domain)
            else:
                logging.warning(f"[WARN] No IPs found for {host_domain}. Hosts file will not be updated.")

        
        # 2. M3U Generation
        streams = fetch_live_streams(host_url, username, password)
        if streams:
            # Pass the arguments to the generation function
            generate_m3u(streams, host_url, username, password, m3u_path, 
                         set_chmod=args.chmod, 
                         do_clean=args.clean,
                         m3u_type=m3u_type)
        else:
            logging.warning(f"[WARN] Server {server_id:02d} did not return any stream data.")
            
        logging.info(f"--- [SERVER {server_id:02d}] Processing complete ---")


if __name__ == "__main__":
    main()
