@echo off
echo Uruchamianie Gym Tracker...
echo Otworz przegladarke na http://localhost:5000
echo Nacisnij CTRL+C aby zakonczyc.
echo.

if not exist "venv" (
    echo Tworzenie srodowiska wirtualnego...
    python -m venv venv
    call venv\Scripts\activate
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
    pip install -r requirements.txt
)

python app.py
pause
