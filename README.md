* Build and Setup Instructions *

** WINDOWS **

Follow these steps to set up the development environment and compile the application.

1. Prerequisites
Python 3.11: Ensure Python 3.11 is installed. You can download it from python.org.
Ensure is installed and configured in your System PATH.

2. Project Setup
Download project from Git or clone

In PowerShell
cd <Project DIR>

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# For PowerShell:
.\venv\Scripts\Activate.ps1
# For CMD:
.\venv\Scripts\activate.bat

3. Install Dependencies
Once the virtual environment is active (venv), run the following commands:

PowerShell
# Upgrade pip to the latest version
python -m pip install --upgrade pip

# Install required packages
pip install wxPython
pip install pysqlcipher3-binary
pip install Pillow bs4 openpyxl requests pyinstaller

4. Verification and Building

# Update your code in database_logic.py
# From: from pysqlcipher3 import dbapi2 as sqlite3
# To:   from sqlcipher3 import dbapi2 as sqlite3

Test Run:
python main.py

If the application starts successfully, use PyInstaller to build the .exe file using your spec file:

pyinstaller main.spec



*----------------------------------*

** LINUX **

sudo apt update

sudo apt install build-essential tcl-dev autoconf automake libtool openssl libssl-dev python3-wxgtk4.0 

git clone https://github.com/sqlcipher/sqlcipher.git
cd sqlcipher

# собираем с поддержкой fts3
./configure \
    CFLAGS="-DSQLITE_HAS_CODEC \
            -DSQLITE_TEMP_STORE=2 \
            -DSQLITE_ENABLE_FTS3 \
            -DSQLITE_ENABLE_FTS4 \
            -DSQLITE_ENABLE_MATH_FUNCTIONS \
            -DSQLITE_EXTRA_INIT=sqlcipher_extra_init \
            -DSQLITE_EXTRA_SHUTDOWN=sqlcipher_extra_shutdown" \
    LDFLAGS="-lcrypto"
make
sudo make install

sudo mkdir -p /usr/local/include/sqlcipher
sudo ln -sf /usr/local/include/sqlite3.h /usr/local/include/sqlcipher/sqlite3.h
sudo ln -sf /usr/local/include/sqlite3ext.h /usr/local/include/sqlcipher/sqlite3ext.h

sudo ln -sf /usr/local/lib/libsqlite3.so /usr/local/lib/libsqlcipher.so
sudo ln -sf /usr/local/lib/libsqlite3.so.3.50.4 /usr/local/lib/libsqlcipher.so.3

python3 -m venv --system-site-packages venv

source venv/bin/activate

python -m pip install --upgrade pip setuptools wheel
export CFLAGS="-I/usr/local/include"i
export LDFLAGS="-L/usr/local/lib -lcrypto"
pip install --no-binary :all: git+https://github.com/rigglemania/pysqlcipher3

cd awardswx_dir

#  добавить в venv/bin/activate
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

# запуск
python main.py

pip install openpyxl requests Pyinstaller
