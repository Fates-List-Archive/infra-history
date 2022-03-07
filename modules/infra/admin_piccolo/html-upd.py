import sys
import time
import os
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler, FileSystemEventHandler
import requests

class Updater(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory or not event.src_path:
            return
        print(f"Posting HTML Update {event}")
        requests.get("http://localhost:10000/_new_html")

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else 'lynx-ui.html'
    observer = Observer()
    observer.schedule(Updater(), path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()
