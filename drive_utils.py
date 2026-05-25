import os
import io
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/drive']

def get_drive_service():
    token_json = os.getenv("GOOGLE_TOKEN_JSON")
    if token_json:
        creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
    else:
        with open("token.json", "r") as f:
            creds = Credentials.from_authorized_user_info(json.load(f), SCOPES)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Guardar el token renovado para que no expire en el próximo uso
        if not os.getenv("GOOGLE_TOKEN_JSON"):
            with open("token.json", "w") as f:
                f.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)


def descargar_archivo(file_id, destino_local):
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    
    with open(destino_local, 'wb') as f:
        downloader = MediaIoBaseDownload(f, request, chunksize=50*1024*1024)  # 50MB por chunk
        done = False
        while not done:
            status, done = downloader.next_chunk()
            pct = int(status.progress() * 100)
            print(f"Descargando desde Drive... {pct}%", flush=True)
    
    # Verificar que el archivo se descargo completo
    tam = os.path.getsize(destino_local)
    if tam < 1024 * 1024:  # menos de 1MB = algo salio mal
        raise Exception(f"Archivo descargado muy pequeño ({tam} bytes) — descarga incompleta")
    
    print(f"Descarga completa: {destino_local} ({tam / (1024*1024*1024):.2f}GB)", flush=True)


def subir_archivo(ruta_local, nombre_drive, carpeta_id=None):
    service = get_drive_service()
    metadata = {'name': nombre_drive}
    if carpeta_id:
        metadata['parents'] = [carpeta_id]
    media = MediaFileUpload(ruta_local, mimetype='video/mp4', resumable=True, chunksize=50*1024*1024)
    file = service.files().create(
        body=metadata, media_body=media, fields='id,webViewLink'
    ).execute()
    link = file.get('webViewLink')
    print(f"Subido a Drive: {link}", flush=True)
    return file.get('id'), link


def listar_carpeta(carpeta_id):
    service = get_drive_service()
    results = service.files().list(
        q=f"'{carpeta_id}' in parents and trashed=false",
        fields="files(id, name, size, createdTime)"
    ).execute()
    return results.get('files', [])

def crear_carpeta(service, nombre, parent_id):
    metadata = {
        'name': nombre,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = service.files().create(body=metadata, fields='id').execute()
    return folder.get('id')
