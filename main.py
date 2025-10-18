# main.py
import multiprocessing
from server import run_server
from ui import run_ui

def main():
    # Start the Flask server in a separate, daemonized process
    print("Starting server process...")
    server_process = multiprocessing.Process(target=run_server, daemon=True)
    server_process.start()

    # Start the Tkinter UI in the main process
    print("Starting UI process...")
    run_ui()

if __name__ == '__main__':
    # This is required for multiprocessing to work correctly when bundled with PyInstaller
    multiprocessing.freeze_support()
    main()