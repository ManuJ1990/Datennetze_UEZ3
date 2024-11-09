import sys
import socket
import os
import urllib.parse  # Für URL-Decoding
import mimetypes  # Für Content-Type Bestimmung

HOST = ''
PORT = 8080
BUFFER_SIZE = 1024


def main():
    if len(sys.argv) != 2:
        print("Fehler! Verwendung: python3 HttpServer.py <Wurzelverzeichnis>")
        sys.exit(1)

    root_directory = sys.argv[1]
    # Konvertiere den Pfad in einen absoluten Pfad
    root_directory = os.path.abspath(root_directory)
    print(f"Server-Wurzelverzeichnis ist gesetzt auf: {root_directory}")

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"Server hochgefahren. Warte auf eingehende Verbindungen auf Port {PORT}...")

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"Eingehende Verbindung von {client_address}")

        handle_client(client_socket, root_directory)


def handle_client(client_socket, root_directory):
    try:
        request_data = b''
        while True:
            data = client_socket.recv(BUFFER_SIZE)
            if not data:
                break
            request_data += data
            if b'\r\n\r\n' in request_data:
                break

        request_text = request_data.decode('iso-8859-1')
        print("Anfrage erhalten:")
        print(request_text)

        request_lines = request_text.split('\r\n')
        request_line = request_lines[0]
        headers = {}

        for line in request_lines[1:]:
            if line == '':
                break
            header_parts = line.split(':', 1)
            if len(header_parts) == 2:
                header_name = header_parts[0].strip()
                header_value = header_parts[1].strip()
                headers[header_name] = header_value

        # Schritt 3: Extrahieren des Pfads aus der Request-Line
        parts = request_line.split()
        if len(parts) != 3:
            raise ValueError("Ungültige Request-Line")

        method, path, http_version = parts
        print(f"Methode: {method}")
        print(f"Pfad: {path}")
        print(f"HTTP-Version: {http_version}")

        if method != 'GET':
            # Nur GET-Methode wird unterstützt
            response = "HTTP/1.1 405 Method Not Allowed\r\n\r\n"
            client_socket.sendall(response.encode('utf-8'))
            return

        # Schritt 4: Überprüfen, ob der angegebene Pfad existiert
        # URL-Decoding des Pfads
        path = urllib.parse.unquote(path)

        # Sicherheitsmaßnahme: Pfad normalisieren und verhindern, dass er aus dem Wurzelverzeichnis herausführt
        requested_path = os.path.normpath(path)
        # Entferne führende Schrägstriche und Backslashes
        requested_path = requested_path.lstrip('/\\')
        full_path = os.path.join(root_directory, requested_path)

        # Für Debugging: Ausgabe der Pfade
        print(f"Requested Path: {requested_path}")
        print(f"Full Path: {full_path}")

        # Überprüfen, ob der full_path innerhalb des root_directory liegt
        if not os.path.commonpath([os.path.abspath(full_path), root_directory]) == root_directory:
            raise FileNotFoundError

        if os.path.isfile(full_path):
            # Datei existiert, Inhalt zurückgeben
            with open(full_path, 'rb') as f:
                content = f.read()

            # Content-Type bestimmen
            content_type, _ = mimetypes.guess_type(full_path)
            if content_type is None:
                content_type = 'application/octet-stream'

            # HTTP-Response erstellen
            response_header = 'HTTP/1.1 200 OK\r\n'
            response_header += f'Content-Type: {content_type}\r\n'
            response_header += f'Content-Length: {len(content)}\r\n'
            response_header += '\r\n'

            # Header und Inhalt senden
            client_socket.sendall(response_header.encode('iso-8859-1') + content)
        else:
            # Datei nicht gefunden, 404 senden
            send_error_response(client_socket, 404, root_directory)

    except FileNotFoundError:
        # 404 senden, wenn Datei nicht gefunden oder Pfad außerhalb des Wurzelverzeichnisses
        send_error_response(client_socket, 404, root_directory)
    except Exception as e:
        print(f"Fehler beim Verarbeiten der Anfrage: {e}")
        # 500 senden bei anderen Fehlern
        send_error_response(client_socket, 500, root_directory)
    finally:
        client_socket.close()


def send_error_response(client_socket, status_code, root_directory):
    if status_code == 404:
        status_message = 'Not Found'
        error_file = '404.html'
    elif status_code == 500:
        status_message = 'Internal Server Error'
        error_file = '500.html'
    else:
        status_message = 'Error'
        error_file = None

    # Pfad zur Fehlerdatei ermitteln
    if error_file:
        error_file_path = os.path.join(root_directory, error_file)
        if os.path.isfile(error_file_path):
            with open(error_file_path, 'rb') as f:
                content = f.read()
        else:
            content = f'<html><body><h1>{status_code} {status_message}</h1></body></html>'.encode('utf-8')
    else:
        content = f'<html><body><h1>{status_code} {status_message}</h1></body></html>'.encode('utf-8')

    # HTTP-Response erstellen
    response_header = f'HTTP/1.1 {status_code} {status_message}\r\n'
    response_header += 'Content-Type: text/html\r\n'
    response_header += f'Content-Length: {len(content)}\r\n'
    response_header += '\r\n'

    # Header und Inhalt senden
    client_socket.sendall(response_header.encode('iso-8859-1') + content)


if __name__ == "__main__":
    main()
