import json
import os
import sys
import threading
import time
import re

# Dipendenze esterne con fallback di messaggi utili
try:
    from mctools import RCONClient
except Exception as e:
    print("(Error): modulo mancante 'mctools'.\n"
          "Suggerimento: crea un virtualenv e installa le dipendenze:\n"
          "  python3 -m venv .venv && source .venv/bin/activate\n"
          "  pip install -U pip && pip install -r requirements.txt\n"
          "Oppure: pip install mctools colorama",
          file=sys.stderr)
    sys.exit(1)

try:
    from colorama import Fore, init
except Exception:
    # Se colorama non è installato, proseguiamo senza colori
    class _NoColor:
        BLACK = RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ""
    def init(*args, **kwargs):
        return None
    Fore = _NoColor()

# Rileva Windows e importa moduli specifici se disponibili
try:
    import ctypes  # solo su Windows per titolo console
    import msvcrt  # solo su Windows per input con asterischi
    IS_WINDOWS = True
except Exception:
    ctypes = None
    msvcrt = None
    IS_WINDOWS = False

# Inizializza Colorama
init(autoreset=True)

# Titolo della console e configurazioni base
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

if IS_WINDOWS and hasattr(ctypes, 'windll'):
    try:
        ctypes.windll.kernel32.SetConsoleTitleW('RCON CLIENT')
    except Exception:
        pass
else:
    # Prova a impostare il titolo su terminali compatibili (xterm)
    try:
        sys.stdout.write("\33]0;RCON CLIENT\a")
        sys.stdout.flush()
    except Exception:
        pass

AsciiArt = f'{Fore.GREEN}' + r"""
 ______     ______     ______     __   __   
/\  == \   /\  ___\   /\  __ \   /\ "-.\ \  
\ \  __<   \ \ \____  \ \ \/\ \  \ \ \-.  \ 
 \ \_\ \_\  \ \_____\  \ \_____\  \ \_\\"\_\
  \/_/ /_/   \/_____/   \/_____/   \/_/ \/_/
""" + Fore.RESET 
print(AsciiArt.strip())

config_file_path = 'config.json'


# --- Funzioni di configurazione ---
def load_config():
    """Carica il file di configurazione (config.json). Se non esiste, lo crea con la configurazione di default."""
    if not os.path.exists(config_file_path):
        print(f'{Fore.YELLOW}(Warning): Configuration file not found, creating a new one...{Fore.RESET}')
        create_default_config()
    with open(config_file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


def create_default_config():
    """Crea un file di configurazione con valori di default."""
    default_config = {
        "servers": [
            {"port": 25575, "log_file": "path to your server log file"},
            {"port": 25575, "log_file": "path to your server log file"}
        ]
    }
    with open(config_file_path, 'w', encoding='utf-8') as file:
        json.dump(default_config, file, indent=4)


# --- Funzioni per l'RCON Client ---
def setup_rcon_client(host, port, password):
    rc = RCONClient(host, port=port)
    return rc.login(password)


def send_rcon_command(rc, cmd):
    try:
        response = rc.command(cmd).encode('utf-8').decode('utf-8')
        print(f'(Info): {response}', end='')
        if 'Unknown or incomplete command' in response or '<--[HERE]' in response:
            print()
        return response
    except Exception as e:
        print(f'{Fore.RED}(Error): Error sending RCON command: {e}{Fore.RESET}', end='')
        print('\r')
        return f'Error sending RCON command: {e}'


def display_help():
    print(f"How to enable RCON on your server: ")
    print(f'1. Open the server.properties file and set to {Fore.GREEN}true{Fore.RESET} enable-rcon=false')
    print(f'2. Set an RCON {Fore.YELLOW}port{Fore.RESET} --> rcon-port=****')
    print(f'3. Set an RCON {Fore.RED}password{Fore.RESET} --> rcon-password=********')
    print(f'Now you can connect to the server remotely, from any PC with this app. :)\n')


# --- Funzioni di utilità ---
def input_password_with_stars(prompt):
    """Input password: su Windows mostra asterischi, altrove usa getpass."""
    if IS_WINDOWS and msvcrt is not None:
        print(prompt, end='', flush=True)
        password = ''
        while True:
            char = msvcrt.getch()
            if char in (b'\r', b'\n'):
                break
            elif char == b'\x08' and password:
                password = password[:-1]
                print('\b \b', end='', flush=True)
            else:
                try:
                    password += char.decode('utf-8', errors='ignore')
                except Exception:
                    continue
                print('*', end='', flush=True)
        print()
        return password
    else:
        import getpass
        return getpass.getpass(prompt)


# --- Funzioni principali ---
def get_login_info():
    while True:
        ip = input(f'Enter the server {Fore.CYAN}IP{Fore.RESET}: ')
        if not ip:
            print(f'{Fore.RED}(Error): IP cannot be empty, please enter your IP.{Fore.RESET}')
            continue
        if ip != 'localhost' and not re.match(r'^(\d{1,3}\.){3}\d{1,3}$', ip) and '.' not in ip:
            print(f'{Fore.RED}(Error): Invalid IP/hostname. Please enter a valid IPv4 address, domain, or "localhost".{Fore.RESET}')
            continue
        try:
            port_input = input(f'Enter the RCON {Fore.YELLOW}port{Fore.RESET}: ')
            if not port_input:
                print(f'{Fore.RED}(Error): Port cannot be empty.{Fore.RESET}')
                continue
            port = int(port_input)
            if not 0 < port <= 65535:
                print(f'{Fore.RED}(Error): Invalid port, please enter a number between 0 and 65535.{Fore.RESET}')
                continue
        except ValueError:
            print(f'{Fore.RED}(Error): Port must be a number.{Fore.RESET}')
            continue
        passw = input_password_with_stars(f'Enter the RCON {Fore.RED}password{Fore.RESET}: ')
        if not passw:
            print(f'{Fore.RED}(Error): Password cannot be empty.{Fore.RESET}')
            continue
        return ip, port, passw


def setup_terminal_rcon():
    while True:
        ip, port, passw = get_login_info()
        rc = RCONClient(ip, port=port)
        if rc.login(passw):
            print(f'[*] {Fore.GREEN}Connected{Fore.RESET} to {ip}:{port}. Type "exit" to close the process.')
            return rc, port
        print(f'{Fore.RED}(Error): Connection failed, please check your details and try again.{Fore.RESET}')


def terminal_loop(rc, port):
    config = load_config()
    
    # Se il 'log_file' non esiste nel config o è vuoto, usa una configurazione di default
    log_file_path = next((s['log_file'] for s in config["servers"] if s['port'] == port and 'log_file' in s), None)

    if not log_file_path:
        print(f'{Fore.YELLOW}(Warning): Log file not specified for port {port}. Continuing without log reading.{Fore.RESET}')
        stop_log_thread = None
    else:
        stop_log_thread = threading.Event()
        log_thread = threading.Thread(target=read_log_file, args=(log_file_path, stop_log_thread), daemon=True)
        log_thread.start()

    while True:
        command = input('> ').strip()
        if not command:
            continue
        if command.lower() == 'exit':
            print('[*] RCON Client shutting down')
            if stop_log_thread:
                stop_log_thread.set()
                log_thread.join()
            break
        send_rcon_command(rc, command)


def read_log_file(log_file_path, stop_event):
    try:
        with open(log_file_path, 'r', encoding='utf-8') as file:
            file.seek(0, os.SEEK_END)
            while not stop_event.is_set():
                line = file.readline()
                if line:
                    print(f'\r{Fore.GREEN}{line.strip()}{Fore.RESET}', end='\n> ', flush=True)
                else:
                    time.sleep(0.1)
    except FileNotFoundError:
        print(f'{Fore.RED}(Error): Log file not found at {log_file_path}{Fore.RESET}')
    except Exception as e:
        print(f'{Fore.RED}(Error): Error reading log file: {e}{Fore.RESET}')


def start_rcon_service():
    while True:
        print('[*] Type "login" to access the server, "?" for help.')
        user_input = input('> ').strip().lower()

        if user_input == '?':
            display_help()
        elif user_input == 'login':
            print('[*] Enter authentication information to access the server')
            rc, port = setup_terminal_rcon()
            terminal_loop(rc, port)
        elif user_input == 'exit':
            print('[*] Closing the program...')
            break
        else:
            print(f'{Fore.RED}(Error): Invalid input. Type "login" to proceed, "?" for help.{Fore.RESET}')
    
    sys.exit(0)


if __name__ == '__main__':
    start_rcon_service()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('[*] Closing...')
