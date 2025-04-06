#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
import platform
import argparse
import re
import venv 

# --- Configuration ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(PROJECT_ROOT, ".venv")
SRC_DIR = os.path.join(PROJECT_ROOT, "TwitterGatherDataFollowers", "userRyersonU")
LIB_DIR = os.path.join(PROJECT_ROOT, "lib")
CLASSES_DIR = os.path.join(PROJECT_ROOT, "classes")

REQUIREMENTS_FILE = os.path.join(PROJECT_ROOT, "requirements.txt")

POM_FILE = os.path.join(PROJECT_ROOT, "pom.xml")
JAVA_MAIN_CLASS = "jade.Boot"
JAVA_MAIN_AGENT = "controller:TwitterGatherDataFollowers.userRyersonU.ControllerAgent"

REQUIRED_PYTHON_VERSION_TUPLE = (3, 9)
REQUIRED_PYTHON_VERSION_STR = "3.9"

# Toggleable for logging
VERBOSE = False

# run cmd as a python subprocess
def run_command(cmd, cwd=PROJECT_ROOT, check=True, capture_output_override=None, text=True, env=None):
    global VERBOSE
    print(f"--- Running command: {' '.join(map(str, cmd))}")
    capture = not VERBOSE
    if capture_output_override is not None: capture = capture_output_override
    stdout_pipe = subprocess.PIPE if capture else None
    stderr_pipe = subprocess.PIPE if capture else None
    try:
        cmd_str = [str(c) for c in cmd]
        process = subprocess.run(
            cmd_str, cwd=cwd, check=check, stdout=stdout_pipe, stderr=stderr_pipe,
            text=text if capture else None, env=env or os.environ,
        )
        return process
    except FileNotFoundError:
        print(f"Error: Command '{cmd[0]}' not found. Is it installed and in PATH?"); sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error: Command failed with exit code {e.returncode}")
        if capture:
             if hasattr(e, 'stdout') and e.stdout: print("--- Captured stdout: ---\n" + e.stdout)
             if hasattr(e, 'stderr') and e.stderr: print("--- Captured stderr: ---\n" + e.stderr)
        sys.exit(1)

# check venv executable
def get_python_executable():
    if platform.system() == "Windows":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    else:
        return os.path.join(VENV_DIR, "bin", "python")

# check interpreter version
def get_python_version_details(python_exe):
    if not os.path.exists(python_exe): return None, None
    try:
        result = run_command([python_exe, "--version"], capture_output_override=True, text=True, check=True)
        version_string = result.stdout.strip()
        match = re.search(r"Python (\d+)\.(\d+)", version_string)
        major_minor = (int(match.group(1)), int(match.group(2))) if match else None
        return version_string, major_minor
    except Exception as e:
        print(f"Error detecting Python version for {python_exe}: {e}"); return "Error", None

# create venv for dependencies
def setup_venv():
    print(f"Ensuring Python {REQUIRED_PYTHON_VERSION_STR} virtual environment exists at {VENV_DIR}...")
    if not os.path.exists(VENV_DIR):
        print(f"Creating virtual environment in {VENV_DIR}...")
        try:
             # Ensure parent directory exists if VENV_DIR includes subdirs
             os.makedirs(os.path.dirname(VENV_DIR), exist_ok=True)
             venv.create(VENV_DIR, with_pip=True)
             print("Virtual environment created.")
             venv_python_exe = get_python_executable()
             if not os.path.exists(venv_python_exe):
                  print(f"Error: Venv creation seemed to succeed, but '{venv_python_exe}' not found!")
                  sys.exit(1)
        except Exception as e:
             print(f"Error creating virtual environment: {e}")
             sys.exit(1)
    else:
        print("Virtual environment already exists.")
        venv_python_exe = get_python_executable()
        if os.path.exists(venv_python_exe):
             version_str, version_tuple = get_python_version_details(venv_python_exe)
             if version_tuple != REQUIRED_PYTHON_VERSION_TUPLE:
                   print(f"Warning: Existing venv at '{VENV_DIR}' is {version_str}, not the required {REQUIRED_PYTHON_VERSION_STR}.")
                   print("         If issues occur, run 'clean' then 'install' using Python {REQUIRED_PYTHON_VERSION_STR}.")
        else:
             print(f"Warning: Venv directory exists but Python executable '{venv_python_exe}' not found.")


# Install maven and python dependencies
def install_dependencies():
    print("\n--- Java Dependencies (Maven) ---")
    if not os.path.exists(POM_FILE):
        print(f"Warning: {POM_FILE} not found. Skipping Maven dependency download.")
    else:
        print(f"Found {POM_FILE}. Downloading dependencies to {LIB_DIR}...")
        os.makedirs(LIB_DIR, exist_ok=True)
        mvn_cmd = ["mvn", "dependency:copy-dependencies", "-DoutputDirectory=" + LIB_DIR]
        try:
             run_command(mvn_cmd)
             print("Maven dependencies downloaded successfully.")
        except FileNotFoundError: print("Error: 'mvn' command not found..."); print("Skipping Maven...")
        except Exception as e: print(f"Error running Maven: {e}"); print("Continuing...")

    print("\n--- Handling Python Dependencies (venv & pip) ---")
    setup_venv() 
    python_exe = get_python_executable()

    print("Installing Python dependencies...")
    if not os.path.exists(REQUIREMENTS_FILE): print(f"Error: {REQUIREMENTS_FILE} not found."); sys.exit(1)

    run_command([python_exe, "-m", "pip", "install", "--upgrade", "pip"])
    run_command([python_exe, "-m", "pip", "install", "-r", REQUIREMENTS_FILE])

    print("Downloading NLTK data (punkt, wordnet)...")
    run_command([python_exe, "-c", "import nltk; nltk.download('punkt', quiet=True); nltk.download('wordnet', quiet=True)"], check=False)
    print("NLTK data download attempt finished.")
    print("Python dependencies installation attempt finished.")

# remove directory classes (common issue causing is old compile)
def clean_classes():
    if os.path.exists(CLASSES_DIR): print(f"Removing directory: {CLASSES_DIR}"); shutil.rmtree(CLASSES_DIR)
    else: print(f"Directory not found, skipping removal: {CLASSES_DIR}")

# remove directory .venv (old dependencies)
def clean_venv():
     if os.path.exists(VENV_DIR): print(f"Removing directory: {VENV_DIR}"); shutil.rmtree(VENV_DIR)
     else: print(f"Directory not found, skipping removal: {VENV_DIR}")

# when migrated to maven fully, can clean the lib dir
# def clean_libs():
#      if os.path.exists(LIB_DIR): print(f"Removing directory: {LIB_DIR}"); shutil.rmtree(LIB_DIR)
#      else: print(f"Directory not found, skipping removal: {LIB_DIR}")

# Compile java sources to classes dir
def compile_java():
    print("Compiling Java source files...")
    if not os.path.exists(CLASSES_DIR): print(f"Creating directory: {CLASSES_DIR}"); os.makedirs(CLASSES_DIR)
    java_files = [os.path.join(root, file) for root, _, files in os.walk(SRC_DIR) for file in files if file.endswith(".java")]
    if not java_files: print(f"Warning: No .java files found in {SRC_DIR}"); return
    lib_jars = []
    if os.path.exists(LIB_DIR): lib_jars = [os.path.join(LIB_DIR, f) for f in os.listdir(LIB_DIR) if f.endswith(".jar")]
    classpath = os.pathsep.join([CLASSES_DIR] + lib_jars)
    compile_cmd = ["javac","-nowarn","-cp", classpath,"-d", CLASSES_DIR] + java_files
    run_command(compile_cmd)
    print("Java compilation finished.")

# get output of java -version command
def get_java_version_details():
    try:
        result = run_command(["java", "-version"], capture_output_override=True, text=True, check=False)
        output = result.stderr
        match = re.search(r'version "(.*?)"', output) or re.search(r'(openjdk|java) version "(.*?)"', output, re.IGNORECASE)
        return match.group(match.lastindex) if match else "Unknown"
    except FileNotFoundError: return None
    except Exception as e: print(f"Error detecting Java version: {e}"); return "Error"

# check java version for compatibility
def get_java_version():
    version_string = get_java_version_details()
    if not version_string or version_string in ["Unknown", "Error"]: return None
    match = re.match(r"(\d+)(?:.(\d+))?", version_string)
    if match:
        major_version = int(match.group(1))
        return int(match.group(2)) if major_version == 1 and match.group(2) else major_version
    return None

# retrieve all java options
def get_java_options(java_major_version):
    java_opts = ["-Xms256m", "-Xmx1424m", "-XX:-UseGCOverheadLimit"]
    jade_opts = ["-jade_domain_df_maxresult", "1500", "-jade_core_messaging_MessageManager_poolsize", "10", "-jade_core_messaging_MessageManager_maxqueuesize", "2000000000", "-jade_core_messaging_MessageManager_deliverytimethreshold", "10000", "-jade_domain_df_autocleanup", "true", "-local-port", "35240"]
    if java_major_version and java_major_version >= 9:
        print("Adding Java 9+ Compatibility Options")
        java_opts.extend(["--add-opens", "java.base/java.lang=ALL-UNNAMED","--add-opens", "java.base/java.io=ALL-UNNAMED","--add-opens", "java.base/java.util=ALL-UNNAMED","--add-opens", "java.base/java.util.concurrent=ALL-UNNAMED","--add-opens", "java.base/sun.nio.ch=ALL-UNNAMED","--add-opens", "java.base/java.net=ALL-UNNAMED"])
    return java_opts, jade_opts

# run java application
def run_java():
    print("Running Java application...")
    if not os.path.exists(CLASSES_DIR): print(f"Error: Classes directory '{CLASSES_DIR}' not found."); sys.exit(1)
    if not os.path.exists(LIB_DIR) or not any(f.endswith(".jar") for f in os.listdir(LIB_DIR)): print(f"Warning: Library directory '{LIB_DIR}' is missing or empty.")
    java_major_version = get_java_version()
    java_opts, jade_opts = get_java_options(java_major_version)
    lib_jars = []
    if os.path.exists(LIB_DIR): lib_jars = [os.path.join(LIB_DIR, f) for f in os.listdir(LIB_DIR) if f.endswith(".jar")]
    classpath = os.pathsep.join([CLASSES_DIR] + lib_jars)
    run_cmd = ["java"] + java_opts + ["-cp", classpath, JAVA_MAIN_CLASS] + jade_opts + [JAVA_MAIN_AGENT]
    run_command(run_cmd, check=True)
    print("Java application finished or was interrupted.")

# print environment info
def show_info():
    print("\n--- Environment Information ---")
    java_version = get_java_version_details(); print(f"Java Version: {java_version or 'Not Found'}")
    maven_version = get_maven_version_details(); print(f"Maven Version: {maven_version or 'Not Found'}") # Need definition from prev answer
    print(f"Required Python Venv Version: {REQUIRED_PYTHON_VERSION_STR}")
    venv_python_exe = get_python_executable()
    if os.path.exists(VENV_DIR):
        venv_python_version, venv_version_tuple = get_python_version_details(venv_python_exe)
        status = ""
        if venv_version_tuple != REQUIRED_PYTHON_VERSION_TUPLE: status = f" [MISMATCH! Expected {REQUIRED_PYTHON_VERSION_STR}]" # Should not happen if installed correctly
        if venv_python_version: print(f"Python (venv): {venv_python_version} (at {venv_python_exe}){status}")
        else: print(f"Python (venv): Venv exists but error getting version from {venv_python_exe}")
    else: print(f"Python (venv): Not found (run 'install' to create)")
    system_python_version, _ = get_python_version_details(sys.executable); print(f"Python (System): {system_python_version} (at {sys.executable})")
    print("\n--- Key Paths ---")
    # print paths to each thing
    print(f"Project Root:    {os.path.abspath(PROJECT_ROOT)}")
    print(f"Virtual Env:     {os.path.abspath(VENV_DIR)}")
    print(f"Java Libs:       {os.path.abspath(LIB_DIR)}")
    print(f"Java Classes:    {os.path.abspath(CLASSES_DIR)}")
    print(f"Java Sources:    {os.path.abspath(SRC_DIR)}")
    print(f"Maven POM File:  {os.path.abspath(POM_FILE)}")
    print(f"Python Req File: {os.path.abspath(REQUIREMENTS_FILE)}")
    print("-" * 29 + "\n")

# check mvn version
def get_maven_version_details():
    try:
        result = run_command(["mvn", "-v"], capture_output_override=True, text=True, check=True)
        match = re.search(r"Apache Maven ([\d\.]+)", result.stdout)
        return match.group(1) if match else "Unknown (parse failed)"
    except FileNotFoundError: return None
    except Exception as e: print(f"Error detecting Maven version: {e}"); return "Error"


if __name__ == "__main__":

    current_python_version = sys.version_info[:2]
    if current_python_version != REQUIRED_PYTHON_VERSION_TUPLE:
        print(f"Error: This script must be run with Python {REQUIRED_PYTHON_VERSION_STR}.")
        print(f"You are currently using Python {sys.version_info.major}.{sys.version_info.minor} ({sys.executable})")
        print("\nPlease invoke the script using your Python 3.9 executable, for example:")
        if platform.system() == "Windows":
            print("  py -3.9 build.py <command>")
            print("  (or potentially: python3.9 build.py <command>)")
        else:
            print(f"  python{REQUIRED_PYTHON_VERSION_STR} build.py <command>")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Build/run script (REQUIRES Python 3.9 to execute)", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("command", choices=["install", "rebuild", "clean", "run", "compile", "setup", "info"], help="Action...")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output.")
    args = parser.parse_args()
    VERBOSE = args.verbose
    if VERBOSE: print(f"--- Verbose mode enabled (running under Python {sys.version_info.major}.{sys.version_info.minor}) ---")

    if args.command == "install": install_dependencies()
    elif args.command == "clean": clean_classes(); clean_venv(); print("Project cleaned.")
    elif args.command == "compile": compile_java()
    elif args.command == "rebuild": clean_classes(); compile_java(); print("Project rebuilt.")
    elif args.command == "setup": install_dependencies(); compile_java(); print("Project setup complete.")
    elif args.command == "info": show_info()
    elif args.command == "run":
        # Basic checks before run
        if not os.path.exists(VENV_DIR): print("Warning: Python venv not found. Run 'install' first."); sys.exit(1) # Make this stricter for run
        if not os.path.exists(CLASSES_DIR): print(f"Classes directory '{CLASSES_DIR}' not found. Compiling..."); compile_java()
        if not os.path.exists(LIB_DIR) or not any(f.endswith(".jar") for f in os.listdir(LIB_DIR)): print(f"Warning: Java libs '{LIB_DIR}' missing/empty.")
        run_java()

    print("Script finished.")
