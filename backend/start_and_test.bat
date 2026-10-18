@echo off
cd D:\projects\CommunityEmergencyResponse\CommunityEmergencyResponse\backend
python manage.py runserver 127.0.0.1:8001 > server.log 2>&1
timeout /t 3 >nul
python test_apis.py
timeout /t 2 >nul
taskkill /f /im python.exe >nul 2>&1