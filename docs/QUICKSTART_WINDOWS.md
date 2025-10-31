# Telegram Bot – Szybki Start (Windows 11)

Ten dokument prowadzi przez pełną, powtarzalną instalację i uruchomienie projektu na nowym komputerze (bez ręcznych poprawek).

## Wymagania
- Windows 11
- Python 3.12+ (dodany do PATH)
- Git

## 0) Klonowanie repo
```powershell
git clone https://github.com/pizdziaty-garfild/tb.git
cd tb
```

## 1) Virtualenv i zależności
```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 2) Bootstrap projektu (katalogi, pliki bazowe)
```powershell
# Utworzy data/, logs/, certs/, alembic/versions/, skopiuje .env jeśli brak
scripts\bootstrap.ps1
```

## 3) Konfiguracja .env
Edytuj `.env`:
- BOT_TOKEN=... (z @BotFather)
- ENC_MASTER_KEY=... (silny klucz 32+ znaków)
- ADMIN_USERS=TwojeTelegramID (np. 123456789)
- OWNER_ID=TwojeTelegramID

Generowanie ENC_MASTER_KEY (jedna z metod):
```powershell
# Python (polecane)
python -c "import secrets; print(secrets.token_urlsafe(48))"

# PowerShell (RNG + base64)
$bytes = New-Object byte[] 48; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes); [Convert]::ToBase64String($bytes)

# OpenSSL
openssl rand -base64 48
```

## 4) Migracje bazy danych
```powershell
# Alembic używa w migracjach synchronicznego sterownika sqlite+pysqlite
# (env.py wymusza to automatycznie)
alembic upgrade head
```

Jeśli zobaczysz błąd "unable to open database file":
```powershell
mkdir data, logs
alembic upgrade head
```

## 5) Uruchomienie bota
```powershell
python main.py
```

Test komend:
- /start → "Bot działa. /info po więcej"
- /info → "Info: wersja 1.0.0"
- /status → "Status OK"

## 6) Tryb produkcyjny (webhook)
W `.env` ustaw `BOT_MODE=webhook` i skonfiguruj:
```env
WEBHOOK_URL=https://twojadomena.pl
WEBHOOK_PORT=8443
TLS_CERT_PATH=certs/cert.pem
TLS_KEY_PATH=certs/private.key
```
Uruchom:
```powershell
scripts\run_webhook.ps1
```

## 7) Polecenia developerskie
```powershell
# Formatowanie i typy
black .
isort .
mypy .

# Testy (gdy dojdą)
pytest -v
```

## 8) Problemy i rozwiązania
- psycopg[binary]==3.2.1 – brak binary dla Windows: naprawiono na psycopg[binary]>=3.2.10 w requirements.txt
- aiosqlite – dodano do requirements, bo runtime używa sqlite+aiosqlite
- greenlet required przy Alembic – env.py wymusza sqlite+pysqlite w migracjach (sync), runtime nadal async
- brak katalogu data/ – naprawa: scripts\bootstrap.ps1 lub ręcznie `mkdir data`

## 9) Bezpieczeństwo
- `.env` nie commituj – plik jest na liście `.gitignore`
- Ustaw NTFS ACL na `.env` (tylko Twój użytkownik)
- ENC_MASTER_KEY trzymaj w menedżerze haseł; rotacja będzie dostarczona skryptem `scripts/rotate_secrets.ps1`

## 10) Co dalej
- Rozszerzenie admin panelu (/pusher, /groups, /logs, /time, /ex_time)
- Dodanie DST-safe schedulera i pełnego rate limiter
- Dodanie testów i CI

W razie problemów: uruchom `scripts\bootstrap.ps1`, a następnie `alembic upgrade head` i `python main.py`.