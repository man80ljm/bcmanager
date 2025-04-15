


打包命令：
pyinstaller --add-data "database\schema.sql;database" --icon=logo.ico --hidden-import numpy --hidden-import pandas --hidden-import win32com --hidden-import pywin32 --hidden-import PyQt5.QtWidgets --hidden-import resources -F -w main.py

打包需要：pip install --upgrade pyinstaller
pip install --upgrade pywin32
保证：pywin32 是最新版本：PyInstaller 是最新版本：

账号：bc
密码：5900145