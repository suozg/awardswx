# AWARDS v.4.1

Програма для роботи з нагородженнями

![Awards_4.1](screenshots/Screenshot%202025-06-21%2015.28.26.png)

----

# Download 
https://github.com/suozg/awardswx/releases/latest

![Приклад бази даних](awards_0v4e.db)

Встановлення не потрібне, працює так.

Виконати програму з цим файлом (пароль 1)
```
awardswx.exe -c awards_0v4e.db
```

або через ярлик:
1. Знайдіть файл awardswx.exe у провіднику. Натисніть на нього правою кнопкою миші та оберіть Надіслати (Send to) > Робочий стіл (створити ярлик).

2. Перейдіть на робочий стіл, натисніть праву кнопку миші на новому ярлику та оберіть Властивості (Properties).
- Перейдіть на вкладку Ярлик (Shortcut).
- Знайдіть поле Об'єкт (Target). Там уже буде вказано повний шлях до програми в лапках.
- Поставте курсор у кінець рядка (після лапок), додайте пробіл і впишіть ваші параметри: -c awards_0v4e.db.

Рядок має виглядати приблизно так:
"C:\Path\To\Your\Folder\awardswx.exe" -c awards_0v4e.db

3. Налаштування робочої папки. Оскільки ви вказуєте файл бази даних awards_0v4e.db без повного шляху, програма шукатиме його в "Робочій папці".

У полі Робоча папка (Start in) переконайтеся, що вказано шлях до папки, де лежить і екзешник, і файл .db.

Якщо база даних лежить в іншому місці, краще вказати повний шлях і до неї в полі "Об'єкт":
...awardswx.exe" -c "C:\Users\Admin\Documents\awards_0v4e.db"


-------
# Build and Setup Instructions

## WINDOWS

Follow these steps to set up the development environment and compile the application.

1. Prerequisites
Python 3.11: Ensure Python 3.11 is installed. You can download it from python.org.
Ensure is installed and configured in your System PATH.

2. Project Setup               
    2.1 Download project from Git or clone

    2.2 In PowerShell or CMD
   ```
        cd Project_DIR 
   ```
    2.3 Create a virtual environment
         
   ```
        python -m venv venv

   ```
    2.4 Activate the virtual environment
      
   ```
        #For PowerShell:                    
            .\venv\Scripts\Activate.ps1

        #For CMD:              
            .\venv\Scripts\activate.bat

   ```
4. Install Dependencies
Once the virtual environment is active (venv), run the following commands:

   ```
        python -m pip install --upgrade pip

   ```
    3.1 Install required packages

   ```
        pip install wxPython sqlcipher3-wheels Pillow bs4 openpyxl requests           

   ```
4. Verification and Building

    4.1 Test
    
   ```
        python main.py

   ```
    4.2 If the application starts successfully, use PyInstaller to build the .exe file using your spec file:
        
   ```
        pip install pyinstaller
        pyinstaller main.spec

   ```



## LINUX

   ```
    sudo apt update             
    sudo apt install sqlcipher 
    
    python3 -m venv --system-site-packages venv             

    # добавить в venv/bin/activate системние пакети:            
        export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH              

    source venv/bin/activate               
    
   ```

проверка

   ```
    cd awardswx_dir
    python main.py

    если ошибка - установить модули:
    
    python -m pip install --upgrade pip setuptools wheel               
    pip install wxPython sqlcipher3-binary Pillow bs4 openpyxl requests 

   ```
    
компиляция

   ```
    pip install pyinstaller          
    pyinstaller main.spec

   ```
