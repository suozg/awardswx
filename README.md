pip list
Package                   Version
------------------------- ----------
altgraph                  0.17.4
babel                     2.17.0
beautifulsoup4            4.11.2
certifi                   2025.4.26
chardet                   5.1.0
charset-normalizer        3.4.2
deprecation               2.0.7
et_xmlfile                2.0.0
html5lib                  1.1
idna                      3.10
img2pdf                   0.4.4
lxml                      4.9.2
numpy                     1.24.2
olefile                   0.46
openpyxl                  3.1.5
packaging                 23.0
pdfarranger               1.9.2
pikepdf                   6.0.0+dfsg
pillow                    11.2.1
pip                       23.0.1
pycairo                   1.20.1
Pygments                  2.14.0
PyGObject                 3.42.2
pyinstaller               6.14.0
pyinstaller-hooks-contrib 2025.4
pysqlcipher3              1.2.0
python-dateutil           2.8.2
python-docx               1.1.2
ranger-fm                 1.9.3
requests                  2.32.3
setuptools                66.1.1
six                       1.16.0
soupsieve                 2.3.2
tkcalendar                1.6.1
typing_extensions         4.14.0
ufw                       0.36.2
urllib3                   2.4.0
webencodings              0.5.1
wheel                     0.45.1
wxPython                  4.2.0

----------
sudo apt update

sudo apt install python3-wxgtk4.0 sqlcipher

sudo apt-get install -f

#create venv:
python3 -m venv --system-site-packages venv

source venv/bin/activate

cd awardswx_dir

python main.py

