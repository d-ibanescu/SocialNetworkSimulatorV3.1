#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Startup and Build Script for SocialNetworkSimulatorV3

Automates setup, compilation, and running of the Java application.
Handles Python venv, pip packages, Maven dependencies, and Java compilation.

Usage:
  python build.py <command> [-v | --help]

Commands:
  install       Set up Python venv, install Python/Java dependencies.
  compile       Compile Java source code. Checks for JDK.
  run           Run the Java application. Checks prerequisites.
  rebuild       Clean Java classes, then compile.
  setup         Run 'install' then 'compile'. Full first-time setup.
  clean         Remove Java classes and Python venv.
  clean-java    Remove compiled Java classes directory only.
  clean-python  Remove Python virtual environment directory only.
  info          Display detected versions (Java, Maven, Python) and paths.
  help          Display this help message.

Options:
  -v, --verbose   Show detailed command execution output.
  -h, --help      Show this help message and exit.

Requires:
  - Python 3.9 or 3.10 to run this script.
  - Java Development Kit (JDK) 8 or higher (for 'compile', 'run').
  - Apache Maven (for 'install').
"""

import os
import sys
import subprocess
import shutil
import platform
import argparse
import re
import venv
import textwrap
import datetime

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
MIN_JAVA_VERSION = 8
ALLOWED_PYTHON_VERSIONS = [(3, 9), (3, 10)]
ALLOWED_PYTHON_VERSIONS_STR = " or ".join([".".join(map(str, v)) for v in ALLOWED_PYTHON_VERSIONS])

# --- Global State ---
VERBOSE = False

# --- Helper Functions ---

def pinfo(message):
    """Prints an informational message."""
    print(f"[INFO] {message}")

def pwarn(message):
    """Prints a warning message."""
    print(f"[WARN] {message}")

def perr(message, suggestion=None, exit_code=1):
    """Prints an error message and exits."""
    print(f"\n[ERROR] {message}", file=sys.stderr)
    if suggestion:
        print(f"        Suggestion: {suggestion}", file=sys.stderr)
    print("\nScript aborted.", file=sys.stderr)
    sys.exit(exit_code)

def pv(message):
    """Prints a message only if verbose mode is enabled."""
    global VERBOSE
    if VERBOSE:
        print(f"  [VERBOSE] {message}")

def check_tool(command, tool_name, install_url=None, required_for_cmd=None):
    """Checks if a command-line tool is available; exits with guidance if not."""
    pinfo(f"Checking for '{tool_name}'...")
    if shutil.which(command):
        pinfo(f"'{tool_name}' found.")
        return True
    else:
        error_msg = f"Required tool '{tool_name}' ('{command}') was not found in your system's PATH."
        suggestion = f"Please install '{tool_name}'"
        if required_for_cmd:
             suggestion += f" (required for the '{required_for_cmd}' command)"
        suggestion += "."
        if install_url:
            suggestion += f"\n        Installation guide: {install_url}"
        else:
            suggestion += "\n        Refer to the official documentation for installation instructions."
        perr(error_msg, suggestion)

def run_cmd(cmd, cwd=PROJECT_ROOT, check=True, capture_output_override=None, text=True, env=None, error_msg_on_fail="Command execution failed"):
    """Runs a command as a subprocess with improved error reporting."""
    use_shell = False
    if platform.system() == "Windows":
        use_shell = True
    global VERBOSE
    cmd_str_display = ' '.join(map(str, cmd))
    pv(f"Running command: {cmd_str_display} in {cwd}")
    if env and env != os.environ:
        pv("Using modified environment (e.g., for venv PATH)")

    capture = not VERBOSE
    if capture_output_override is not None: capture = capture_output_override
    stdout_pipe = subprocess.PIPE if capture else None
    stderr_pipe = subprocess.PIPE if capture else None

    try:
        cmd_list = [str(c) for c in cmd]
        process = subprocess.run(
            cmd_list, cwd=cwd, check=False,
            stdout=stdout_pipe, stderr=stderr_pipe, text=text,
            shell=use_shell,
            env=env or os.environ,
        )

        if check and process.returncode != 0:
            error_details = f"{error_msg_on_fail} (Exit Code: {process.returncode})"
            error_details += f"\n        Command: {cmd_str_display}"
            if process.stdout: error_details += "\n--- Captured STDOUT ---\n" + process.stdout.strip() + "\n-----------------------"
            if process.stderr: error_details += "\n--- Captured STDERR ---\n" + process.stderr.strip() + "\n-----------------------"
            perr(error_details, suggestion="Check the output above for clues. Ensure all prerequisites are met.")
        return process
    except FileNotFoundError:
        perr(f"Command '{cmd[0]}' not found.",
             suggestion=f"Is '{cmd[0]}' installed and included in your system's PATH environment variable?")
    except Exception as e:
         perr(f"An unexpected error occurred while trying to run '{cmd[0]}': {e}",
              suggestion="Check the command and system environment.")

def py_exe_path(venv_dir=VENV_DIR):
    """Gets the expected path to the Python executable within the venv."""
    if platform.system() == "Windows":
        return os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        return os.path.join(venv_dir, "bin", "python")

def fetch_py_version(python_exe):
    """Gets the version string and tuple (major, minor) for a Python executable."""
    if not os.path.exists(python_exe):
        pv(f"Python executable not found at: {python_exe}")
        return None, None
    try:
        result = run_cmd([python_exe, "--version"], capture_output_override=True, text=True, check=True,
                         error_msg_on_fail=f"Failed to get version from {python_exe}")
        version_string = (result.stdout or result.stderr).strip()
        match = re.search(r"Python (\d+)\.(\d+)(?:\.\d+)?", version_string)
        if match:
            major_minor = (int(match.group(1)), int(match.group(2)))
            return version_string, major_minor
        else:
            pwarn(f"Could not parse Python version from string: '{version_string}'")
            return version_string, None
    except Exception as e:
        pwarn(f"Could not determine Python version for {python_exe}: {e}")
        return "Error", None

def venv_env_vars():
    """Creates a modified environment dictionary for running subprocesses in the venv context."""
    pv(f"Attempting to create execution environment based on venv: {VENV_DIR}")
    if not os.path.isdir(VENV_DIR):
        pwarn(f"Virtual environment directory not found at {VENV_DIR}. Cannot create venv-specific environment.")
        return None

    venv_python = py_exe_path()
    if not os.path.exists(venv_python):
        pwarn(f"Venv directory exists but Python executable not found at {venv_python}.")
        return None

    venv_scripts_path = os.path.dirname(venv_python)
    modified_env = os.environ.copy()
    original_path = modified_env.get('PATH', '')
    modified_env['PATH'] = venv_scripts_path + os.pathsep + original_path
    pv(f"Prepended to PATH: {venv_scripts_path}")
    modified_env['VIRTUAL_ENV'] = os.path.abspath(VENV_DIR)
    pv(f"Set VIRTUAL_ENV: {modified_env['VIRTUAL_ENV']}")
    if 'PYTHONHOME' in modified_env:
        del modified_env['PYTHONHOME']
        pv("Removed PYTHONHOME from subprocess environment for venv compatibility.")
    return modified_env

def fetch_java_version_str():
    """Detects installed Java version string. Returns None if not found."""
    try:
        result = run_cmd(["java", "-version"], capture_output_override=True, text=True, check=False)
        if result.returncode != 0 and "command not found" not in (result.stderr or result.stdout).lower():
             pwarn(f"Command 'java -version' failed. Output:\n{result.stderr or result.stdout}")
             return "Error"
        output = result.stderr or result.stdout
        match = re.search(r'(?:java|openjdk)\s+version\s+"(.*?)"', output, re.IGNORECASE)
        if match: return match.group(1)
        match_simple = re.search(r'version\s+"(.*?)"', output) # Fallback
        if match_simple: return match_simple.group(1)
        pv(f"Could not parse Java version from output:\n{output}")
        return "Unknown format"
    except FileNotFoundError: return None
    except Exception as e: pwarn(f"Error detecting Java version: {e}"); return "Error"

def fetch_java_major_ver(version_string):
    """Extracts the major Java version number (e.g., 8, 11, 17) from a string."""
    if not version_string or version_string in ["Unknown format", "Error", None]: return None
    match = re.match(r"(\d+)(?:.(\d+))?", version_string)
    if match:
        major = int(match.group(1))
        return int(match.group(2)) if major == 1 and match.group(2) else major # Handle 1.8 format
    return None

def fetch_mvn_version_str():
    """Detects installed Maven version string. Returns None if not found."""
    try:
        result = run_cmd(["mvn", "--version"], capture_output_override=True, text=True, check=False)
        if result.returncode != 0 and "command not found" not in (result.stderr or result.stdout).lower():
             pwarn(f"Command 'mvn --version' failed. Output:\n{result.stderr or result.stdout}")
             return "Error"
        output = result.stdout or result.stderr
        match = re.search(r"Apache Maven ([\d\.]+)", output)
        if match: return match.group(1)
        pv(f"Could not parse Maven version from output:\n{output}")
        return "Unknown format"
    except FileNotFoundError: return None
    except Exception as e: pwarn(f"Error detecting Maven version: {e}"); return "Error"

# --- Core Script Functions ---

def ensure_venv():
    """Ensures the Python virtual environment exists and is compatible."""
    pinfo(f"Ensuring Python {ALLOWED_PYTHON_VERSIONS_STR} virtual environment exists at: {VENV_DIR}")
    venv_python_exe = py_exe_path()

    if not os.path.isdir(VENV_DIR) or not os.path.exists(venv_python_exe):
        pinfo(f"Virtual environment not found or incomplete. Creating new one...")
        os.makedirs(os.path.dirname(VENV_DIR), exist_ok=True)
        if os.path.exists(VENV_DIR):
             pwarn(f"Removing existing incomplete venv directory: {VENV_DIR}")
             shutil.rmtree(VENV_DIR)
        try:
            venv.create(VENV_DIR, with_pip=True)
            pinfo("Virtual environment created successfully.")
            if not os.path.exists(py_exe_path()):
                 perr("Venv creation reported success, but Python executable is missing inside!",
                      suggestion=f"Check permissions or disk space. Try running 'clean-python' then 'install'.")
        except Exception as e:
            perr(f"Failed to create virtual environment: {e}",
                 suggestion="Ensure you have permissions to write to the project directory.")
    else:
        pinfo("Virtual environment found.")
        version_str, version_tuple = fetch_py_version(venv_python_exe)
        if version_tuple and version_tuple not in ALLOWED_PYTHON_VERSIONS:
            pwarn(f"Existing venv at '{VENV_DIR}' uses Python {version_str}, "
                  f"but this project requires Python {ALLOWED_PYTHON_VERSIONS_STR}.")
            pwarn(f"This might cause issues. If problems occur, run 'clean-python', "
                  f"then run 'install' again (using Python {ALLOWED_PYTHON_VERSIONS_STR}).")
        elif not version_tuple:
             pwarn(f"Could not determine Python version for the existing venv at {venv_python_exe}.")
        else:
             pinfo(f"Existing venv uses Python {version_str} (compatible).")

def install():
    """Installs Java (Maven) and Python (pip) dependencies."""
    pinfo("\n--- Step 1: Installing Java Dependencies (via Maven) ---")
    check_tool("mvn", "Apache Maven",
               install_url="https://maven.apache.org/install.html",
               required_for_cmd="install")

    if not os.path.exists(POM_FILE):
        pwarn(f"Maven POM file not found: {POM_FILE}. Skipping Java dependency download.")
    else:
        pinfo(f"Found {POM_FILE}. Downloading Java dependencies to: {LIB_DIR}")
        os.makedirs(LIB_DIR, exist_ok=True)
        mvn_cmd = ["mvn", "dependency:copy-dependencies", "-DoutputDirectory=" + LIB_DIR, "-DskipTests=true", "-q"]
        try:
            run_cmd(mvn_cmd, error_msg_on_fail="Maven dependency download failed")
            pinfo("Maven dependencies downloaded successfully.")
        except Exception as e:
            perr(f"An unexpected error occurred during Maven execution: {e}",
                 suggestion="Check your network connection and Maven setup.")

    pinfo("\n--- Step 2: Setting up Python Environment & Dependencies (venv + pip) ---")
    ensure_venv()
    python_exe = py_exe_path()
    if not os.path.exists(python_exe):
        perr(f"Python executable not found in venv: {python_exe}",
             suggestion="Try running 'clean-python' then 'install'.")

    pinfo("Upgrading pip in venv...")
    run_cmd([python_exe, "-m", "pip", "install", "--upgrade", "pip"], error_msg_on_fail="Failed to upgrade pip")

    pinfo(f"Installing Python packages from: {REQUIREMENTS_FILE}")
    if not os.path.exists(REQUIREMENTS_FILE):
        perr(f"Python requirements file not found: {REQUIREMENTS_FILE}",
             suggestion="Ensure the file exists in the project root.")
    run_cmd([python_exe, "-m", "pip", "install", "-r", REQUIREMENTS_FILE], error_msg_on_fail="Failed to install Python packages")
    pinfo("Python packages installed successfully.")

    pinfo("Downloading NLTK data (punkt, wordnet)...")
    nltk_cmd_str = "import nltk; nltk.download('punkt', quiet=True); nltk.download('wordnet', quiet=True)"
    result = run_cmd([python_exe, "-c", nltk_cmd_str], check=False, error_msg_on_fail="NLTK download command error")
    if result.returncode == 0:
         pinfo("NLTK data download command executed.")
    else:
         pwarn("NLTK data download command failed. Output:")
         if result.stderr: print(result.stderr)
         if result.stdout: print(result.stdout)
         pwarn("Application might fail if NLTK data is missing.")
         pwarn("Suggestion: Check internet connection or run download manually: "
               f"\n        {python_exe} -m nltk.downloader punkt wordnet")
    pinfo("Dependency installation process finished.")

def clean_java_output():
    """Removes the compiled Java classes directory."""
    if os.path.exists(CLASSES_DIR):
        pinfo(f"Removing directory: {CLASSES_DIR}")
        try:
            shutil.rmtree(CLASSES_DIR)
            pinfo("Classes directory removed.")
        except Exception as e:
            perr(f"Failed to remove directory {CLASSES_DIR}: {e}",
                 suggestion="Check permissions or close programs using these files.")
    else:
        pinfo(f"Directory not found, skipping removal: {CLASSES_DIR}")

def clean_py_env():
    """Removes the Python virtual environment directory."""
    if os.path.exists(VENV_DIR):
        pinfo(f"Removing directory: {VENV_DIR}")
        try:
            shutil.rmtree(VENV_DIR)
            pinfo("Virtual environment directory removed.")
        except Exception as e:
            perr(f"Failed to remove directory {VENV_DIR}: {e}",
                 suggestion="Check permissions or ensure venv not active elsewhere.")
    else:
        pinfo(f"Directory not found, skipping removal: {VENV_DIR}")

def compile_java():
    """Compiles the Java source files using javac."""
    pinfo("\n--- Compiling Java Source Code ---")
    check_tool("javac", "Java Compiler (javac)",
               install_url="Search for 'Install JDK 8 or higher'",
               required_for_cmd="compile")
    java_version_str = fetch_java_version_str()
    java_major = fetch_java_major_ver(java_version_str)
    if java_major and java_major < MIN_JAVA_VERSION:
         # This is now an error based on requirement "need any java version >=8"
         perr(f"Detected Java version {java_version_str} (Major: {java_major}). "
              f"Version {MIN_JAVA_VERSION} or higher is required.",
              suggestion="Please install or configure your system to use JDK 8 or newer.")
    elif not java_major and java_version_str not in [None, "Error", "Unknown format"]:
        pwarn(f"Could not determine Java major version from '{java_version_str}'. Ensure it's compatible (>= {MIN_JAVA_VERSION}).")

    pinfo(f"Ensuring output directory exists: {CLASSES_DIR}")
    os.makedirs(CLASSES_DIR, exist_ok=True)

    pinfo(f"Searching for Java source files in: {SRC_DIR}")
    if not os.path.isdir(SRC_DIR): perr(f"Java source directory not found: {SRC_DIR}")
    java_files = [os.path.join(root, file) for root, _, files in os.walk(SRC_DIR) for file in files if file.endswith(".java")]

    if not java_files: pwarn(f"No '.java' files found in {SRC_DIR}. Nothing to compile."); return

    pinfo(f"Found {len(java_files)} Java source files.")
    pv("Source files:\n" + "\n".join(f"  {f}" for f in java_files[:10]) + ("\n  ..." if len(java_files) > 10 else ""))

    lib_jars = []
    if os.path.isdir(LIB_DIR):
        lib_jars = [os.path.join(LIB_DIR, f) for f in os.listdir(LIB_DIR) if f.endswith(".jar")]
        pinfo(f"Found {len(lib_jars)} JARs in: {LIB_DIR}")
    else:
        pwarn(f"Java library directory not found: {LIB_DIR}. Compilation might fail.")

    classpath_entries = [CLASSES_DIR] + lib_jars
    classpath_str = os.pathsep.join(classpath_entries)
    pv(f"Classpath for compilation: {classpath_str}")

    compile_cmd = ["javac", "-Xlint:unchecked", "-encoding", "UTF-8", "-cp", classpath_str, "-d", CLASSES_DIR] + java_files
    pinfo("Starting Java compilation...")
    run_cmd(compile_cmd, error_msg_on_fail="Java compilation failed")
    pinfo("Java compilation finished successfully.")

def java_runtime_opts(java_major_version):
    """Constructs appropriate Java VM options based on the detected major version."""
    java_opts = ["-Xms256m", "-Xmx1424m", "-XX:-UseGCOverheadLimit"]
    jade_opts = [
        "-jade_domain_df_maxresult", "1500", "-jade_core_messaging_MessageManager_poolsize", "10",
        "-jade_core_messaging_MessageManager_maxqueuesize", "2000000000",
        "-jade_core_messaging_MessageManager_deliverytimethreshold", "10000",
        "-jade_domain_df_autocleanup", "true", "-local-port", "35240"
    ]
    pv("Base Java VM Options: " + " ".join(java_opts))
    pv("JADE Options: " + " ".join(jade_opts))

    # Add module opening flags only if Java 9+ is detected
    if java_major_version and java_major_version >= 9:
        pinfo(f"Detected Java {java_major_version}. Adding '--add-opens' flags for compatibility.")
        modules_to_open = [ # Keep comment explaining why these are needed
            "java.base/java.lang", "java.base/java.io", "java.base/java.util",
            "java.base/java.util.concurrent", "java.base/sun.nio.ch", "java.base/java.net"
        ]
        for module_spec in modules_to_open:
            java_opts.extend(["--add-opens", f"{module_spec}=ALL-UNNAMED"])
        pv("Added Java 9+ compatibility options: " + " ".join(java_opts[-len(modules_to_open)*2:]))
    elif java_major_version: # Java 8 or lower detected
         pinfo(f"Detected Java {java_major_version}. No '--add-opens' flags needed.")
    else: # Could not detect version
         pwarn("Could not determine Java major version. Runtime might fail on Java 9+ without '--add-opens' flags.")
    return java_opts, jade_opts

def run():
    """Runs the compiled Java application using the Python venv's environment context."""
    pinfo("\n--- Running the Java Application ---")

    pinfo("Performing pre-run checks...")
    check_tool("java", "Java Runtime Environment (JRE or JDK)",
               install_url="Search for 'Install JDK 8 or higher'",
               required_for_cmd="run")

    java_version_str = fetch_java_version_str()
    java_major = fetch_java_major_ver(java_version_str)
    if java_major and java_major < MIN_JAVA_VERSION:
         perr(f"Detected Java version {java_version_str} (Major: {java_major}). Version {MIN_JAVA_VERSION} or higher is required.",
              suggestion="Please install or configure your system to use JDK 8 or newer.")
    elif not java_major and java_version_str not in [None, "Error", "Unknown format"]:
        pwarn(f"Could not determine Java major version from '{java_version_str}'. Ensure it's compatible (>= {MIN_JAVA_VERSION}).")

    if not os.path.isdir(VENV_DIR): perr(f"Python venv not found: {VENV_DIR}", suggestion="Run 'install' first.")
    if not os.path.isdir(CLASSES_DIR): perr(f"Compiled classes dir not found: {CLASSES_DIR}", suggestion="Run 'compile' or 'setup' first.")
    if not os.listdir(CLASSES_DIR): perr(f"Compiled classes dir is empty: {CLASSES_DIR}", suggestion="Run 'compile' or 'setup' first.")
    if not os.path.isdir(LIB_DIR) or not any(f.endswith(".jar") for f in os.listdir(LIB_DIR)):
        pwarn(f"Java library dir '{LIB_DIR}' missing or empty. Run 'install'. Application might fail.")

    pinfo("Pre-run checks passed.")
    pinfo("Preparing execution environment...")
    java_env = venv_env_vars()
    if not java_env: perr("Failed to create execution environment from Python venv.", suggestion=f"Ensure venv '{VENV_DIR}' is valid. Try 'clean-python' then 'install'.")
    pinfo("Execution environment prepared.")

    lib_jars = []
    if os.path.isdir(LIB_DIR): lib_jars = [os.path.join(LIB_DIR, f) for f in os.listdir(LIB_DIR) if f.endswith(".jar")]
    classpath_entries = [CLASSES_DIR] + lib_jars
    classpath_str = os.pathsep.join(classpath_entries)
    pv(f"Runtime Classpath: {classpath_str}")

    java_opts, jade_opts = java_runtime_opts(java_major)
    run_cmd_list = ["java"] + java_opts + ["-cp", classpath_str, JAVA_MAIN_CLASS] + jade_opts + [JAVA_MAIN_AGENT]

    pinfo("Starting Java application...")
    pv("Full command: " + " ".join(run_cmd_list))

    try:
        process = run_cmd(run_cmd_list, check=False, env=java_env, error_msg_on_fail="Java application execution failed")
        if process.returncode == 0: pinfo("\nJava application finished successfully.")
        else: pwarn(f"\nJava application exited with code: {process.returncode}")
        if not VERBOSE and process.returncode != 0 and process.stderr: print("---\n" + process.stderr.strip() + "\n---")
    except KeyboardInterrupt: pinfo("\nJava application interrupted by user (Ctrl+C).")
    except Exception as e: perr(f"An unexpected error occurred while running Java: {e}")

def info():
    """Displays detected environment information and key project paths."""
    pinfo("\n--- Environment and Project Information ---")

    print("\n[ Tools ]")
    java_version_str = fetch_java_version_str()
    if java_version_str is None: print("  Java: Not Found (Required: JDK 8+)"); print("        Suggestion: Install JDK 8+ and add to PATH.")
    elif java_version_str in ["Error", "Unknown format"]: print(f"  Java: Error detecting version ({java_version_str})")
    else:
        java_major = fetch_java_major_ver(java_version_str)
        status = ""
        if java_major and java_major < MIN_JAVA_VERSION: status = f" [ERROR: Requires {MIN_JAVA_VERSION}+]"
        elif not java_major: status = " [WARN: Could not parse major version]"
        print(f"  Java: {java_version_str}{status} (via 'java -version')")

    mvn_version_str = fetch_mvn_version_str()
    if mvn_version_str is None: print("  Maven: Not Found (Required for 'install')"); print("         Suggestion: Install Apache Maven and add to PATH (https://maven.apache.org/install.html).")
    elif mvn_version_str in ["Error", "Unknown format"]: print(f"  Maven: Error detecting version ({mvn_version_str})")
    else: print(f"  Maven: {mvn_version_str} (via 'mvn --version')")

    print("\n[ Python ]")
    print(f"  Required Version (for script & venv): {ALLOWED_PYTHON_VERSIONS_STR}")
    script_py_ver_str, script_py_ver_tuple = fetch_py_version(sys.executable)
    status_script = ""
    if script_py_ver_tuple not in ALLOWED_PYTHON_VERSIONS: status_script = f" [ERROR: MUST BE {ALLOWED_PYTHON_VERSIONS_STR}]"
    print(f"  Running Script With: {script_py_ver_str or 'Unknown'} (at {sys.executable}){status_script}")

    venv_python_exe = py_exe_path()
    if os.path.exists(VENV_DIR) and os.path.exists(venv_python_exe):
        venv_py_ver_str, venv_py_ver_tuple = fetch_py_version(venv_python_exe)
        status_venv = ""
        if not venv_py_ver_tuple: status_venv = " [WARN: Error getting version]"
        elif venv_py_ver_tuple not in ALLOWED_PYTHON_VERSIONS: status_venv = f" [WARN: Mismatch! Expected {ALLOWED_PYTHON_VERSIONS_STR}. Run 'clean-python' then 'install']"
        print(f"  Virtual Env Python: {venv_py_ver_str or 'Unknown'} (at {venv_python_exe}){status_venv}")
    elif os.path.exists(VENV_DIR): print(f"  Virtual Env Python: Venv dir exists, but exe missing! ({venv_python_exe}). Suggestion: Run 'clean-python' then 'install'.")
    else: print(f"  Virtual Env Python: Not found (at {VENV_DIR}). Suggestion: Run 'install'.")

    print("\n[ Project Paths ]")
    print(f"  Project Root:      {os.path.abspath(PROJECT_ROOT)}")
    print(f"  Python Virtualenv: {os.path.abspath(VENV_DIR)}")
    print(f"  Java Source Dir:   {os.path.abspath(SRC_DIR)}")
    print(f"  Java Libraries:    {os.path.abspath(LIB_DIR)}")
    print(f"  Compiled Classes:  {os.path.abspath(CLASSES_DIR)}")
    print(f"  Maven POM File:    {os.path.abspath(POM_FILE)}")
    print(f"  Python Req. File:  {os.path.abspath(REQUIREMENTS_FILE)}")
    print("\n" + "-" * 40 + "\n")

# --- Main Execution ---

if __name__ == "__main__":
    print(f"--- SocialNetworkSimulatorV3 Build/Run Script (Requires Python {ALLOWED_PYTHON_VERSIONS_STR}) ---")

    current_py_ver_tuple = sys.version_info[:2]
    if current_py_ver_tuple not in ALLOWED_PYTHON_VERSIONS:
        error_msg = (f"This script MUST be executed using Python {ALLOWED_PYTHON_VERSIONS_STR}.\n"
                     f"        You are currently using Python {sys.version_info.major}.{sys.version_info.minor} "
                     f"(from {sys.executable}).")
        suggestion = f"Please re-run using a Python {ALLOWED_PYTHON_VERSIONS_STR} executable.\n"
        if platform.system() == "Windows": suggestion += "        Example: py -3.9 build.py <command> OR py -3.10 build.py <command>"
        else: suggestion += f"        Example: python3.9 build.py <command> OR python3.10 build.py <command>"
        print(f"\n[FATAL ERROR] {error_msg}", file=sys.stderr)
        print(f"\n  Suggestion: {suggestion}", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description=textwrap.dedent(__doc__),
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="Example: python build.py setup -v"
    )
    parser.add_argument(
        "command",
        nargs='?', # Make command optional to allow 'help' to work if no command given (or just --help)
        choices=["install", "compile", "run", "rebuild", "setup", "clean", "clean-java", "clean-python", "info", "help"],
        help=textwrap.dedent(f"""
Action to perform (default: shows help):
  install       - Create/update Python venv ({ALLOWED_PYTHON_VERSIONS_STR}), install pip/Maven deps.
  compile       - Compile Java code ('{os.path.basename(SRC_DIR)}' -> '{os.path.basename(CLASSES_DIR)}'). Needs JDK {MIN_JAVA_VERSION}+.
  run           - Execute Java app. Needs JDK {MIN_JAVA_VERSION}+, classes, venv.
  rebuild       - Clean Java classes, then compile.
  setup         - Run 'install', then 'compile'. For initial setup.
  clean         - Remove Java classes and Python venv.
  clean-java    - Remove only compiled Java classes ('{os.path.basename(CLASSES_DIR)}').
  clean-python  - Remove only Python venv ('{os.path.basename(VENV_DIR)}').
  info          - Show detected versions and project paths.
  help          - Display this help message.
""")
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable detailed output.")
    args = parser.parse_args()
    VERBOSE = args.verbose

    if not args.command or args.command == "help":
        parser.print_help()
        sys.exit(0)

    if VERBOSE: pinfo(f"Verbose mode enabled. Running command '{args.command}'...")

    start_time = datetime.datetime.now()
    pv(f"\n>>> Executing Command: {args.command} <<<")

    try:
        if args.command == "install": install()
        elif args.command == "compile": compile_java()
        elif args.command == "run": run()
        elif args.command == "rebuild":
            clean_java_output()
            compile_java()
            pinfo("Project rebuild complete.")
        elif args.command == "setup":
            install()
            compile_java()
            pinfo("Project setup complete.")
        elif args.command == "clean":
            clean_java_output()
            clean_py_env()
            pinfo("Project clean complete (classes and venv removed).")
        elif args.command == "clean-java":
            clean_java_output()
            pinfo("Java clean complete (classes removed).")
        elif args.command == "clean-python":
            clean_py_env()
            pinfo("Python clean complete (venv removed).")
        elif args.command == "info": info()

        duration = datetime.datetime.now() - start_time
        pv(f">>> Command '{args.command}' finished successfully in {duration.total_seconds():.2f} seconds. <<<")

    except Exception as e:
         perr(f"An unexpected error occurred during command '{args.command}': {e}",
              suggestion="Review script output. If error persists, check script logic or report issue.")

    print("\nScript finished.")
