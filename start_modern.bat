@echo off
setlocal enabledelayedexpansion
REM
REM :: Check if Java version was provided as argument
REM if "%~1" neq "" (
REM     set "jver=%~1"
REM     echo Using specified Java version: %jver%
REM ) else (
REM     :: Auto-detect Java version random windows hack
REM     for /f tokens^=2-5^ delims^=.-_^" %%j in ('java -version 2^>^&1') do (
REM         set "jver=%%j"
REM         goto :breakloop
REM     )
REM     :breakloop
REM     echo Auto-detected Java version: %jver%
REM )
REM
REM :: Set Java options
REM set "JAVA_OPTS=-Xms256m -Xmx14240m -XX:-UseGCOverheadLimit"
REM set "JADE_OPTS=-jade_domain_df_maxresult 1500 -jade_core_messaging_MessageManager_poolsize 10 -jade_core_messaging_MessageManager_maxqueuesize 2000000000 -jade_core_messaging_MessageManager_deliverytimethreshold 10000 -jade_domain_df_autocleanup true -local-port 35240"
REM
REM :: Add Java 9+ compatibility options if needed
REM if %jver% GTR 9 (
REM     set "JAVA_OPTS=%JAVA_OPTS% --add-opens java.base/java.lang=ALL-UNNAMED --add-opens java.base/java.net=ALL-UNNAMED --add-opens java.base/java.io=ALL-UNNAMED --add-opens java.base/java.util=ALL-UNNAMED --add-opens java.base/java.util.concurrent=ALL-UNNAMED --add-opens java.base/sun.nio.ch=ALL-UNNAMED"
REM )
REM
REM echo Checking Python environment...
REM
REM where /q python3 2>nul && (python3 -c "print('ok')" 2>nul | findstr "ok" >nul) 
REM if %ERRORLEVEL% EQU 0 (
REM     set "PYTHON_CMD=python3"
REM     goto :python_found
REM )
REM
REM where /q python 2>nul && (python -c "print('ok')" 2>nul | findstr "ok" >nul)
REM if %ERRORLEVEL% EQU 0 (
REM     set "PYTHON_CMD=python"
REM     goto :python_found
REM )
REM
REM :python_found
REM echo Using Python command: %PYTHON_CMD%
REM
REM :: Check Python version using python modules
REM for /f "tokens=*" %%a in ('%PYTHON_CMD% -c "import sys; print(sys.version_info[0])"') do set major_version=%%a
REM for /f "tokens=*" %%a in ('%PYTHON_CMD% -c "import sys; print(sys.version_info[1])"') do set minor_version=%%a
REM
REM if %major_version% LSS 3 (
REM     echo Python version must be 3.9 or higher. Current version: %major_version%.%minor_version%
REM     exit /b 1
REM )
REM if %major_version% EQU 3 if %minor_version% LSS 9 (
REM     echo Python version must be 3.9 or higher. Current version: %major_version%.%minor_version%
REM     exit /b 1
REM )
REM
REM :: Check and install numpy if needed
REM %PYTHON_CMD% -c "import numpy" 2>nul
REM if %ERRORLEVEL% NEQ 0 (
REM     echo Installing numpy...
REM     %PYTHON_CMD% -m pip install numpy
REM )
REM %PYTHON_CMD% -c "import gensim" 2>nul
REM if %ERRORLEVEL% NEQ 0 (
REM     echo Installing gensim...
REM     %PYTHON_CMD% -m pip install gensim
REM )
REM %PYTHON_CMD% -c "import sklearn" 2>nul
REM if %ERRORLEVEL% NEQ 0 (
REM     echo Installing sklearn...
REM     %PYTHON_CMD% -m pip install scikit-learn
REM )
REM %PYTHON_CMD% -c "import nltk" 2>nul
REM if %ERRORLEVEL% NEQ 0 (
REM     echo Installing nltk...
REM     %PYTHON_CMD% -m pip install nltk
REM     %PYTHON_CMD% -c "import nltk;nltk.download('punkt');nltk.download('punkt_tab')"
REM )
REM %PYTHON_CMD% -c "import seaborn" 2>nul
REM if %ERRORLEVEL% NEQ 0 (
REM     echo Installing seaborn...
REM     %PYTHON_CMD% -m pip install seaborn
REM )
REM %PYTHON_CMD% -c "import matplotlib" 2>nul
REM if %ERRORLEVEL% NEQ 0 (
REM     echo Installing matplotlib...
REM     %PYTHON_CMD% -m pip install matplotlib
REM )
REM
REM %PYTHON_CMD% -c "import ipython" 2>nul
REM if %ERRORLEVEL% NEQ 0 (
REM     echo Installing ipython...
REM     %PYTHON_CMD% -m pip install ipython
REM )
REM :: Compile Java code
REM javac -nowarn -cp "lib/*" -d classes TwitterGatherDataFollowers/userRyersonU/*.java
REM
REM :: Run Java application
REM java %JAVA_OPTS% -cp "lib/*;classes" jade.Boot %JADE_OPTS% controller:TwitterGatherDataFollowers.userRyersonU.ControllerAgent

SET PYTHON_PATH=python
SET SCRIPT_PATH=build.py
%PYTHON_PATH% %SCRIPT_PATH% run -v
