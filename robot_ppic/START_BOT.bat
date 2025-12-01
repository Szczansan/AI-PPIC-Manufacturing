@echo off
title BOT PPIC - JANGAN DICLOSE
echo Sedang menyalakan mesin bot...

:: Pindah ke folder project (Ganti path di bawah ini pakai punya lo)
cd /d "C:\Users\szcza\OneDrive\Documents\1.DATA\PyCharm Doc\Project\Ecosystem Production\robot_ppic"

:: Jalankan Script Python
python alert_bot.py

:: Biar jendela gak langsung nutup kalau error
pause