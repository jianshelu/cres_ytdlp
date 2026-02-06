import os
import subprocess
import sys
import time
import datetime

# ANSI colors for Windows terminal (if supported) or stripped
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def log(msg, color=Colors.OKBLUE):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {color}{msg}{Colors.ENDC}")

def show_progress(current, total, label="Progress", width=40):
    percent = (current / total) * 100
    filled = int(width * current // total)
    bar = "#" * filled + "-" * (width - filled)
    sys.stdout.write(f"\r  {label}: [{bar}] {percent:.0f}%")
    sys.stdout.flush()
    if current == total:
        print()

def read_env():
    """Read .env file manually."""
    env_vars = {}
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    value = value.strip('\'"')
                    env_vars[key.strip()] = value
    return env_vars

def run_ssh_command(ssh_cmd_base, remote_command, description, total_substeps=None):
    from queue import Queue, Empty
    from threading import Thread

    log(f"Step: {description}")
    full_cmd = ssh_cmd_base + [remote_command]
    
    start_time = time.time()
    process = subprocess.Popen(
        full_cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    q = Queue()
    def enqueue_output(out, queue):
        for line in iter(out.readline, ''):
            queue.put(line)
        out.close()

    t = Thread(target=enqueue_output, args=(process.stdout, q))
    t.daemon = True
    t.start()

    current_substep = 0
    
    while process.poll() is None:
        try:
            # Check for new lines without blocking
            while True:
                line = q.get_nowait()
                if "[STAGE" in line:
                    try:
                        parts = line.split("[STAGE")[1].split("]")[0].strip().split("/")
                        current_substep = int(parts[0])
                        if total_substeps is None:
                            total_substeps = int(parts[1])
                    except:
                        pass
        except Empty:
            pass
        
        elapsed = int(time.time() - start_time)
        if total_substeps:
            show_progress(current_substep, total_substeps, f"{description} ({elapsed}s)")
        else:
            pulse = int((time.time() * 2) % 10)
            bar = "-" * pulse + "#" + "-" * (9 - pulse)
            sys.stdout.write(f"\r  {description} running... {elapsed}s [{bar}]")
            sys.stdout.flush()
        time.sleep(0.5)
            
    # Final clear and summary
    print() 
    duration = time.time() - start_time
    
    # Wait for process to end and thread to finish
    process.wait()
    t.join(timeout=1.0)
    
    if process.returncode != 0:
        log(f"Error during {description} (after {duration:.2f}s):", Colors.FAIL)
        # Try to read stderr if we didn't capture it
        try:
            err = process.stderr.read()
            print(err)
        except:
            pass
        return False
        
    log(f"Completed {description} in {duration:.2f}s", Colors.OKGREEN)
    return True

def main():
    # 1. Configuration
    env = read_env()
    
    user = env.get("VAST_USER", "root")
    host = env.get("VAST_HOST", "ssh1.vast.ai")
    port = env.get("VAST_PORT", "12843")
    key_path = env.get("VAST_SSH_KEY", "")
    target_dir = "/workspace"

    # Fix WSL path if present (for Windows compatibility)
    if sys.platform == "win32" and key_path.startswith("/mnt/"):
        parts = key_path.split("/")
        if len(parts) > 2 and len(parts[2]) == 1:
            drive = parts[2]
            rest = "/".join(parts[3:])
            key_path = f"{drive}:/{rest}"
    
    log("========================================", Colors.HEADER)
    log(f"Deploying to {user}@{host} (Port {port})", Colors.HEADER)
    log(f"Target Directory: {target_dir}", Colors.HEADER)
    log(f"Using Key: {key_path}", Colors.HEADER)
    log("========================================", Colors.HEADER)

    # Base SSH command
    ssh_base = ["ssh", "-p", port, "-o", "StrictHostKeyChecking=no"]
    if key_path:
        ssh_base.extend(["-i", key_path])
    ssh_target = f"{user}@{host}"
    
    full_ssh_base = ssh_base + [ssh_target]

    # 1. Check Connection & Python
    log(f"[1/4] Checking connection and remote dependencies...", Colors.HEADER)

    # 2. Check Connection & Dependencies
    log("[1/4] Checking connection and remote dependencies...")
    check_cmd = "command -v tar >/dev/null 2>&1 || { echo 'MISSING_TAR'; exit 1; }"
    if not run_ssh_command(full_ssh_base, check_cmd, "Connection Check"):
        log("Cannot connect or 'tar' is missing on remote.", Colors.FAIL)
        return

    # 3. Sync Files (Tar Pipe)
    log("[2/4] Syncing files (Tar Stream)...")
    # Tar Local
    # Exclude logic for Windows tar might differ, assuming bsdtar (standard on Win10+)
    tar_cmd = ["tar", "-c", 
               "--exclude=.git", "--exclude=.env", "--exclude=node_modules", 
               "--exclude=.next", "--exclude=__pycache__", 
               "--exclude=web/src/data.json", "--exclude=web/public/downloads/*",
               "."]
    
    # Remote Extract
    remote_tar_cmd = f"mkdir -p {target_dir} && cd {target_dir} && tar -x"
    
    try:
        # Create pipeline: Local Tar -> SSH -> Remote Tar
        p1 = subprocess.Popen(tar_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p2 = subprocess.Popen(full_ssh_base + [remote_tar_cmd], stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p1.stdout.close()  # Allow p1 to receive SIGPIPE if p2 exits
        out, err = p2.communicate()
        
        if p2.returncode != 0:
            log("Sync failed!", Colors.FAIL)
            print("Stderr:", err.decode())
            return
        log("Sync complete.")
    except Exception as e:
        log(f"Sync error: {e}", Colors.FAIL)
        return

    # 4. Remote Setup (Install Deps)
    log("[3/4] Installing dependencies remotely...")
    setup_script = f"""
    set -e
    cd {target_dir}
    
    # Fix CRLF in scripts if syncing from Windows
    for f in entrypoint.sh start_remote.sh onstart.sh; do
        if [ -f "$f" ]; then
            sed -i 's/\\r$//' "$f"
            chmod +x "$f"
        fi
    done

    echo "[STAGE 1/5] Installing System Deps..."
    apt-get update -qq >/dev/null
    apt-get install -y ffmpeg curl wget python3-pip psmisc net-tools >/dev/null

    echo "[STAGE 2/5] Installing Node..."
    if ! command -v node &> /dev/null; then
        apt-get install -y nodejs npm >/dev/null
    fi

    echo "[STAGE 3/5] Installing Python Deps..."
    pip3 install --upgrade pip >/dev/null
    pip3 install -r requirements.txt >/dev/null

    echo "[STAGE 4/5] Building Web App..."
    cd web
    npm install >/dev/null
    npm run build
    cd ..
    
    echo "[STAGE 5/5] Refreshing Index..."
    python3 generate_index.py

    echo "Setup Complete."
    """
    
    if not run_ssh_command(full_ssh_base, setup_script, "Remote Setup", total_substeps=5):
        return

    # 5. Start Services
    log("[4/4] Starting Services...")
    start_cmd = f"""
    cd {target_dir}
    chmod +x start_remote.sh onstart.sh entrypoint.sh
    mkdir -p logs
    ./start_remote.sh
    """
    
    if run_ssh_command(full_ssh_base, start_cmd, "Start Services"):
        log("Deployment Finished Successfully!", Colors.OKGREEN)
        log("========================================", Colors.HEADER)
        log("AUTO-STARTUP CONFIGURATION REQUIRED:", Colors.WARNING)
        log("1. Go to Vast.ai Console -> Edit Instance", Colors.WARNING)
        log("2. Set 'On-start script' to: bash /workspace/onstart.sh", Colors.WARNING)
        log("========================================", Colors.HEADER)
        log(f"Access tunnel via: python connect_vast.py", Colors.OKGREEN)

if __name__ == "__main__":
    main()
