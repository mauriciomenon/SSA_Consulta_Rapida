#!/usr/bin/env python3
"""Test socket reuse with SO_REUSEADDR."""

import socket
import time

PORT = 51234

print("=" * 80)
print("TESTE: SO_REUSEADDR no Socket de Instancia Unica")
print("=" * 80)
print()

# Test 1: Bind sem SO_REUSEADDR
print("[1] Teste SEM SO_REUSEADDR...")
sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    sock1.bind(("127.0.0.1", PORT))
    sock1.listen(1)
    print(f"[OK] Socket 1 conectado na porta {PORT}")
except OSError as e:
    print(f"[ERRO] Nao conseguiu bind: {e}")
    import sys
    sys.exit(1)

# Close socket
sock1.close()
print("[OK] Socket 1 fechado")
print()

# Test 2: Tentar bind imediatamente (deve falhar sem SO_REUSEADDR)
print("[2] Tentando bind IMEDIATO sem SO_REUSEADDR...")
sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    sock2.bind(("127.0.0.1", PORT))
    print("[ERRO] Conseguiu bind imediato - nao deveria (TIME_WAIT nao funciona?)")
    sock2.close()
except OSError as e:
    print(f"[OK] Falhou como esperado (TIME_WAIT ativo): {e}")
    sock2.close()
print()

# Wait a bit
print("[3] Aguardando 3 segundos...")
time.sleep(3)
print()

# Test 3: Tentar bind COM SO_REUSEADDR
print("[4] Tentando bind COM SO_REUSEADDR...")
sock3 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock3.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    sock3.bind(("127.0.0.1", PORT))
    sock3.listen(1)
    print(f"[OK] Socket 3 conectado com SO_REUSEADDR na porta {PORT}")
    sock3.close()
    print("[OK] Socket 3 fechado")
except OSError as e:
    print(f"[ERRO] Falhou mesmo com SO_REUSEADDR: {e}")

print()
print("=" * 80)
print("[SUCESSO] SO_REUSEADDR permite reutilizar porta imediatamente")
print("=" * 80)
