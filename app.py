import os
import sys
import subprocess
import time
import json
import shutil
import tarfile
import urllib.request
import zipfile
import stat
import tempfile
import importlib

def run_command(cmd, retries=1, timeout=300):
    """Run a command with retries"""
    for attempt in range(retries):
        try:
            print(f"Attempt {attempt+1}/{retries}: {cmd}")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
            
            if result.returncode == 0:
                print(f"✓ Success: {cmd}")
                if result.stdout.strip():
                    print(f"Output: {result.stdout[:500]}...")
                return True, result.stdout
            else:
                print(f"✗ Failed: {cmd}")
                if result.stderr:
                    print(f"Error: {result.stderr[:500]}...")
                if attempt < retries - 1:
                    print("Retrying after 2 seconds...")
                    time.sleep(2)
                    
        except subprocess.TimeoutExpired:
            print(f"Timeout: {cmd}")
        except Exception as e:
            print(f"Exception: {e}")
    
    return False, ""

def check_command_exists(cmd):
    """Check if a command exists in the system"""
    return shutil.which(cmd) is not None

def add_to_path(path):
    """Add a directory to PATH environment variable"""
    if path and os.path.exists(path) and path not in os.environ["PATH"].split(":"):
        os.environ["PATH"] = f"{path}:{os.environ['PATH']}"
        os.putenv("PATH", os.environ["PATH"])
        print(f"Added {path} to PATH")
        return True
    return False

def install_nodejs_restricted():
    """Specialized Node.js installation for highly restricted environments"""
    print("\n" + "="*60)
    print("INSTALLING NODE.JS IN RESTRICTED ENVIRONMENT")
    print("="*60)
    
    # First check if Node.js is already installed
    node_exists = check_command_exists("node")
    npm_exists = check_command_exists("npm")
    
    if node_exists and npm_exists:
        print("Node.js and npm are already installed")
        run_command("node --version")
        run_command("npm --version")
        return True
    
    # Try all methods in sequence
    methods = [
        install_nodejs_portable_binary,
        install_nodejs_precompiled_binary,
        install_nodejs_static_binary,
        install_nodejs_from_source_simple
    ]
    
    for i, method in enumerate(methods, 1):
        print(f"\nTrying method {i}/{len(methods)}")
        success = method()
        if success:
            print(f"✓ Node.js installed successfully using method {i}")
            return True
        else:
            print(f"✗ Method {i} failed")
    
    print("All Node.js installation methods failed!")
    return False

def install_nodejs_portable_binary():
    """Install portable Node.js binary"""
    print("Downloading portable Node.js binary...")
    
    try:
        # Determine system architecture
        machine = os.uname().machine
        arch = "x64" if machine in ["x86_64", "amd64"] else "arm64" if machine in ["aarch64", "arm64"] else "x64"
        
        # Create directories for installation
        home_dir = os.path.expanduser("~")
        node_dir = os.path.join(home_dir, ".local", "nodejs")
        bin_dir = os.path.join(home_dir, ".local", "bin")
        
        os.makedirs(node_dir, exist_ok=True)
        os.makedirs(bin_dir, exist_ok=True)
        
        # Download Node.js binary (version 20.x)
        version = "20.17.0"
        node_url = f"https://nodejs.org/dist/v{version}/node-v{version}-linux-{arch}.tar.xz"
        print(f"Downloading Node.js {version} for {arch}...")
        
        # Download and extract
        node_tar_path = os.path.join(node_dir, "node.tar.xz")
        urllib.request.urlretrieve(node_url, node_tar_path)
        
        # Extract Node.js
        with tarfile.open(node_tar_path, 'r:xz') as tar:
            tar.extractall(node_dir)
        
        # Remove downloaded archive
        os.remove(node_tar_path)
        
        # Get the extracted directory
        extracted_dir = f"node-v{version}-linux-{arch}"
        node_extracted_path = os.path.join(node_dir, extracted_dir)
        
        # Create symlinks
        node_bin_path = os.path.join(node_extracted_path, "bin", "node")
        npm_bin_path = os.path.join(node_extracted_path, "bin", "npm")
        
        node_link_path = os.path.join(bin_dir, "node")
        npm_link_path = os.path.join(bin_dir, "npm")
        
        # Remove existing symlinks if they exist
        for link_path in [node_link_path, npm_link_path]:
            if os.path.exists(link_path) or os.path.islink(link_path):
                try:
                    os.remove(link_path)
                except:
                    pass
        
        # Create new symlinks
        os.symlink(node_bin_path, node_link_path)
        os.symlink(npm_bin_path, npm_link_path)
        
        # Add to PATH
        add_to_path(bin_dir)
        
        # Verify installation
        if check_command_exists("node") and check_command_exists("npm"):
            print("Portable Node.js installed successfully!")
            run_command("node --version")
            run_command("npm --version")
            return True
            
    except Exception as e:
        print(f"Portable binary method failed: {e}")
    
    return False

def install_nodejs_precompiled_binary():
    """Install precompiled Node.js binary"""
    print("Trying precompiled Node.js binary...")
    
    try:
        # Create installation directory
        install_dir = os.path.join(os.path.expanduser("~"), ".nodejs")
        bin_dir = os.path.join(install_dir, "bin")
        
        os.makedirs(install_dir, exist_ok=True)
        os.makedirs(bin_dir, exist_ok=True)
        
        # Download precompiled binary (different source)
        machine = os.uname().machine
        arch = "x64" if machine in ["x86_64", "amd64"] else "arm64"
        
        # Try different download sources
        download_urls = [
            f"https://github.com/nodejs/node/raw/main/bin/linux-{arch}/node",
            f"https://nodejs.org/download/release/latest/linux-{arch}/node",
            f"https://unofficial-builds.nodejs.org/download/release/latest/linux-{arch}/node"
        ]
        
        node_bin_path = os.path.join(bin_dir, "node")
        
        for url in download_urls:
            try:
                print(f"Downloading from: {url}")
                urllib.request.urlretrieve(url, node_bin_path)
                
                # Make executable
                os.chmod(node_bin_path, 0o755)
                
                # Add to PATH
                add_to_path(bin_dir)
                
                # Test node
                if check_command_exists("node"):
                    print("Precompiled Node.js installed!")
                    run_command("node --version")
                    
                    # Try to get npm separately
                    install_npm_separately(bin_dir)
                    return True
                    
            except Exception as e:
                print(f"Download from {url} failed: {e}")
                continue
                
    except Exception as e:
        print(f"Precompiled binary method failed: {e}")
    
    return False

def install_npm_separately(bin_dir):
    """Install npm separately"""
    try:
        # Download npm separately
        npm_url = "https://registry.npmjs.org/npm/-/npm-10.8.1.tgz"
        npm_tar_path = os.path.join(bin_dir, "npm.tgz")
        
        print("Downloading npm separately...")
        urllib.request.urlretrieve(npm_url, npm_tar_path)
        
        # Extract npm
        with tarfile.open(npm_tar_path, 'r:gz') as tar:
            tar.extractall(bin_dir)
        
        # Create npm symlink
        npm_bin_path = os.path.join(bin_dir, "package", "bin", "npm-cli.js")
        npm_link_path = os.path.join(bin_dir, "npm")
        
        if os.path.exists(npm_bin_path):
            if os.path.exists(npm_link_path) or os.path.islink(npm_link_path):
                try:
                    os.remove(npm_link_path)
                except:
                    pass
            
            os.symlink(npm_bin_path, npm_link_path)
            os.chmod(npm_link_path, 0o755)
            
            print("npm installed separately!")
            run_command("npm --version")
            return True
            
    except Exception as e:
        print(f"Separate npm installation failed: {e}")
    
    return False

def install_nodejs_static_binary():
    """Install static Node.js binary"""
    print("Trying static Node.js binary...")
    
    try:
        # Create installation directory
        install_dir = os.path.join(os.path.expanduser("~"), ".static-node")
        os.makedirs(install_dir, exist_ok=True)
        
        # Determine architecture
        machine = os.uname().machine
        arch = "x64" if machine in ["x86_64", "amd64"] else "arm64"
        
        # Download static binary
        static_url = f"https://github.com/mhart/alpine-node/releases/download/v20.17.0/node-v20.17.0-linux-{arch}.tar.gz"
        static_tar_path = os.path.join(install_dir, "node-static.tar.gz")
        
        print("Downloading static Node.js binary...")
        urllib.request.urlretrieve(static_url, static_tar_path)
        
        # Extract
        with tarfile.open(static_tar_path, 'r:gz') as tar:
            tar.extractall(install_dir)
        
        # Add bin directory to PATH
        bin_dir = os.path.join(install_dir, "bin")
        add_to_path(bin_dir)
        
        # Verify
        if check_command_exists("node"):
            print("Static Node.js installed!")
            run_command("node --version")
            run_command("npm --version")
            return True
            
    except Exception as e:
        print(f"Static binary method failed: {e}")
    
    return False

def install_nodejs_from_source_simple():
    """Simplified Node.js source compilation"""
    print("Trying simplified Node.js source build...")
    
    try:
        # Create build directory
        build_dir = os.path.join(os.path.expanduser("~"), ".node-build")
        os.makedirs(build_dir, exist_ok=True)
        
        # Download Node.js source
        source_url = "https://nodejs.org/dist/v20.17.0/node-v20.17.0.tar.gz"
        source_tar_path = os.path.join(build_dir, "node-src.tar.gz")
        
        print("Downloading Node.js source...")
        urllib.request.urlretrieve(source_url, source_tar_path)
        
        # Extract source
        with tarfile.open(source_tar_path, 'r:gz') as tar:
            tar.extractall(build_dir)
        
        # Configure with minimal options
        source_dir = os.path.join(build_dir, "node-v20.17.0")
        os.chdir(source_dir)
        
        # Try to configure
        print("Configuring Node.js build...")
        success, _ = run_command("./configure --prefix=$HOME/.local/node-built")
        
        if success:
            # Try to build with minimal resources
            print("Building Node.js (this may take a while)...")
            success, _ = run_command("make -j2")  # Use only 2 cores
            
            if success:
                # Install
                success, _ = run_command("make install")
                
                if success:
                    # Add to PATH
                    add_to_path(os.path.expanduser("~/.local/node-built/bin"))
                    
                    if check_command_exists("node"):
                        print("Node.js built from source!")
                        run_command("node --version")
                        run_command("npm --version")
                        return True
        
        # Clean up
        os.chdir("/")
        
    except Exception as e:
        print(f"Source build method failed: {e}")
    
    return False

def install_python_dependencies_safe():
    """Install Python dependencies with safe fallbacks"""
    print("\n" + "="*60)
    print("INSTALLING PYTHON DEPENDENCIES")
    print("="*60)
    
    # First upgrade pip and setuptools
    run_command(f"{sys.executable} -m pip install --upgrade pip setuptools wheel")
    
    # Install packages one by one with individual error handling
    packages = [
        "flask", "aiofiles", "aiohttp", "asyncio", "beautifulsoup4",
        "dnspython", "future==0.18.3", "gitpython", "httpx[http2]",
        "heroku3", "hachoir", "motor==3.3.2", "psutil", "pykeyboard",
        "pymongo==4.6.3", "python-dotenv", "pyyaml==6.0.1", "requests",
        "qrcode", "tgcrypto", "gpytranslate", "googlesearch-python",
        "telegraph", "speedtest-cli", "unidecode", "urllib3", "wget",
        "yt-dlp", "bing-image-urls", "Cloudscraper",
        "pillow>=9.0.0", "py-tgcalls>=0.9.0", "SafoneAPI>=1.0.60",
        "youtube-search-python>=1.6.0", "spotipy>=2.0.0"
    ]
    
    # Git repositories
    git_repos = [
        "git+https://github.com/KurimuzonAkuma/pyrogram@dev",
        "git+https://github.com/alexmercerind/youtube-search-python@main",
        "git+https://github.com/joetats/youtube_search@master"
    ]
    
    all_success = True
    
    # Install regular packages
    for package in packages:
        print(f"Installing {package}...")
        success, _ = run_command(f"{sys.executable} -m pip install --no-cache-dir --prefer-binary {package}")
        if not success:
            success, _ = run_command(f"{sys.executable} -m pip install --no-cache-dir {package}")
            if not success:
                print(f"Warning: Failed to install {package}")
                all_success = False
    
    # Install git repositories
    for repo in git_repos:
        print(f"Installing from {repo}...")
        success, _ = run_command(f"{sys.executable} -m pip install --no-cache-dir {repo}")
        if not success:
            print(f"Warning: Failed to install from {repo}")
            all_success = False
    
    # Special handling for problematic packages
    problem_packages = [
        ("lxml", "lxml"),
        ("search_engine_parser", "search_engine_parser"),
        ("bing_image_downloader", "bing_image_downloader"),
        ("MukeshAPI", "MukeshAPI"),
        ("telethon==1.33.1", "telethon"),
        ("ffmpeg-python", "ffmpeg-python")
    ]
    
    for package_cmd, package_name in problem_packages:
        success, _ = run_command(f"{sys.executable} -m pip install --no-cache-dir --prefer-binary {package_cmd}")
        if not success:
            success, _ = run_command(f"{sys.executable} -m pip install --no-cache-dir {package_cmd}")
            if not success and package_cmd == "lxml":
                success, _ = run_command(f"{sys.executable} -m pip install --no-cache-dir lxml --install-option=\"--without-cython\"")
        
        if not success:
            print(f"Warning: Failed to install {package_name}")
            all_success = False
    
    return all_success

def start_application():
    """Start the main application with live logging"""
    print("\n" + "="*80)
    print("STARTING MAIN APPLICATION")
    print("="*80)
    
    # Try different entry points
    entry_points = [
        [sys.executable, "-m", "SONALI"],
        [sys.executable, "main.py"],
        [sys.executable, "app.py"],
        [sys.executable, "bot.py"],
        [sys.executable, "server.py"],
        [sys.executable, "index.py"],
        [sys.executable, "start.py"]
    ]
    
    for entry_point in entry_points:
        # Check if the entry point exists (for files)
        if len(entry_point) > 1 and not entry_point[1].startswith("-"):
            if not os.path.exists(entry_point[1]):
                print(f"Skipping {entry_point[1]} - file not found")
                continue
        
        print(f"Trying: {' '.join(entry_point)}")
        
        try:
            process = subprocess.Popen(
                entry_point,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Stream output in real-time
            for line in process.stdout:
                print(line, end='')
                sys.stdout.flush()
            
            process.wait()
            if process.returncode == 0:
                return True
                
        except Exception as e:
            print(f"Failed to start: {e}")
    
    return False

if __name__ == "__main__":
    print("="*80)
    print("ULTIMATE INSTALLATION FOR RESTRICTED ENVIRONMENTS")
    print("="*80)
    
    # Install Node.js using specialized methods
    node_installed = install_nodejs_restricted()
    
    # Install Python dependencies
    python_success = install_python_dependencies_safe()
    
    # Start the application
    app_started = start_application()
    
    print("\n" + "="*80)
    print("INSTALLATION SUMMARY")
    print("="*80)
    print(f"Node.js installed: {'✓' if node_installed else '✗'}")
    print(f"Python dependencies: {'✓' if python_success else '✗'}")
    print(f"Application started: {'✓' if app_started else '✗'}")
    
    if not app_started:
        print("\nTroubleshooting tips:")
        print("1. Check if your main application file exists")
        print("2. Check for any error messages above")
        print("3. Try running manually: python -m SONALI or python main.py")
        
        # Show available files
        print("\nAvailable files:")
        run_command("ls -la")