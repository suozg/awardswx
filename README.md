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
