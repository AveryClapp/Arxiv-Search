import threading
import click
import time

def spinner_context(message):
    """Simple spinner context manager"""
    class Spinner:
        def __init__(self, message):
            self.message = message
            self.spinning = False
            self.spinner_thread = None

        def __enter__(self):
            self.spinning = True
            self.spinner_thread = threading.Thread(target=self._spin)
            self.spinner_thread.daemon = True
            click.echo(f"{self.message}... ", nl=False)
            self.spinner_thread.start()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.spinning = False
            if self.spinner_thread:
                self.spinner_thread.join()
            click.echo("✓")

        def _spin(self):
            chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
            i = 0
            while self.spinning:
                click.echo(f"\r{self.message}... {chars[i % len(chars)]}", nl=False)
                i += 1
                time.sleep(0.1)

    return Spinner(message)
