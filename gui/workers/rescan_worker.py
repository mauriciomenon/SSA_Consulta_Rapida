# gui/workers/rescan_worker.py
# Worker thread for database rescanning

import os
import sys
import subprocess
import threading
import time
from queue import Queue, Empty
from PyQt6.QtCore import QThread, pyqtSignal


class RescanWorker(QThread):
    """
    Worker thread to execute database rescan without blocking UI.

    Uses threading to read stdout/stderr simultaneously (Windows compatible).

    Signals:
        output_line: Emitted for each line of stdout
        error_line: Emitted for each line of stderr
        progress: Emitted with progress updates
        finished_success: Emitted when completed successfully
        finished_error: Emitted when an error occurs
    """

    output_line = pyqtSignal(str)
    error_line = pyqtSignal(str)
    progress = pyqtSignal(int, str)  # percentage, message
    finished_success = pyqtSignal()
    finished_error = pyqtSignal(str)

    def __init__(self, main_py_path, project_root):
        super().__init__()
        self.main_py_path = main_py_path
        self.project_root = project_root
        self._should_stop = False

    def _enqueue_output(self, pipe, queue, pipe_name):
        """Read lines from pipe and put in queue (runs in thread)."""
        try:
            for line in iter(pipe.readline, ''):
                if line:
                    queue.put((pipe_name, line.rstrip()))
        except Exception as e:
            queue.put((pipe_name, f"[ERRO lendo {pipe_name}: {e}]"))
        finally:
            pipe.close()

    def run(self):
        """Execute rescan in background thread."""
        try:
            self.output_line.emit("=== Iniciando Reescaneamento ===")
            self.output_line.emit(f"Executando: {self.main_py_path}")
            self.output_line.emit("")
            self.progress.emit(5, "Iniciando processo...")

            # Execute main.py with real-time output streaming
            process = subprocess.Popen(
                [sys.executable, self.main_py_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                cwd=self.project_root,
                universal_newlines=True
            )

            # Create queue and threads to read stdout and stderr simultaneously
            # This avoids deadlock and works on Windows
            output_queue = Queue()

            stdout_thread = threading.Thread(
                target=self._enqueue_output,
                args=(process.stdout, output_queue, 'stdout'),
                daemon=True
            )
            stderr_thread = threading.Thread(
                target=self._enqueue_output,
                args=(process.stderr, output_queue, 'stderr'),
                daemon=True
            )

            stdout_thread.start()
            stderr_thread.start()

            stdout_lines = []
            stderr_lines = []
            last_progress = 5

            # Read output until process finishes
            while True:
                if self._should_stop:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    self.finished_error.emit("Processo cancelado pelo usuario")
                    return

                # Check if process has finished
                retcode = process.poll()

                # Read all available output from queue
                has_output = False
                try:
                    while True:
                        try:
                            pipe_name, line = output_queue.get_nowait()
                            has_output = True

                            if pipe_name == 'stdout':
                                self.output_line.emit(line)
                                stdout_lines.append(line)

                                # Update progress based on output
                                if "Processando" in line or "Processing" in line:
                                    last_progress = min(90, last_progress + 5)
                                    self.progress.emit(last_progress, line[:50])
                                elif "Importacao concluida" in line or "Import complete" in line:
                                    self.progress.emit(95, "Importacao concluida")
                                elif "arquivo" in line.lower() or "file" in line.lower():
                                    last_progress = min(85, last_progress + 2)
                                    self.progress.emit(last_progress, line[:50])

                            elif pipe_name == 'stderr':
                                self.error_line.emit(line)
                                stderr_lines.append(line)

                        except Empty:
                            break

                except Exception as e:
                    self.error_line.emit(f"Erro ao ler saida: {e}")

                # If process finished and no more output, exit
                if retcode is not None and not has_output:
                    # Give threads a moment to flush remaining output
                    time.sleep(0.1)

                    # Try one more time to get any remaining output
                    try:
                        while True:
                            pipe_name, line = output_queue.get_nowait()
                            if pipe_name == 'stdout':
                                self.output_line.emit(line)
                                stdout_lines.append(line)
                            elif pipe_name == 'stderr':
                                self.error_line.emit(line)
                                stderr_lines.append(line)
                    except Empty:
                        pass

                    break

                # Small sleep to prevent busy waiting
                time.sleep(0.05)

            # Process finished
            if retcode == 0:
                self.progress.emit(100, "Concluido com sucesso")
                self.output_line.emit("")
                self.output_line.emit("=== Reescaneamento Concluido ===")
                self.finished_success.emit()
            else:
                error_msg = f"Processo terminou com erro (codigo {retcode})"
                if stderr_lines:
                    error_msg += f"\nUltimos erros:\n" + "\n".join(stderr_lines[-5:])
                self.finished_error.emit(error_msg)

        except Exception as e:
            self.finished_error.emit(f"Erro ao executar reescaneamento: {e}")

    def stop(self):
        """Request thread to stop."""
        self._should_stop = True
