import os
from pathlib import Path
from urllib.parse import quote

import requests

from machineconfig.utils.cloud.onedrive.auth import make_graph_request, get_drive_id


def push_to_onedrive(local_path: str, remote_path: str, section: str) -> bool:
    local_file = Path(local_path)
    if not local_file.exists():
        print(f"Local file does not exist: {local_path}")
        return False
    if not local_file.is_file():
        print(f"Path is not a file: {local_path}")
        return False
    if not remote_path.startswith("/"):
        remote_path = "/" + remote_path
    remote_dir = os.path.dirname(remote_path)
    if remote_dir and remote_dir != "/":
        create_remote_directory(remote_dir, section=section)
    try:
        file_size = local_file.stat().st_size
        if file_size < 4 * 1024 * 1024:
            return simple_upload(local_file, remote_path, section=section)
        else:
            return resumable_upload(local_file, remote_path, section=section)
    except Exception as e:
        print(f"Error uploading file: {e}")
        return False


def simple_upload(local_file: Path, remote_path: str, section: str) -> bool:
    try:
        file_content = local_file.read_bytes()
        encoded_path = quote(remote_path, safe="/")
        drive_id = get_drive_id(section)
        endpoint = f"drives/{drive_id}/root:{encoded_path}:/content"
        response = make_graph_request("PUT", endpoint, section=section, data=file_content)
        if response.status_code in [200, 201]:
            print(f"Successfully uploaded: {local_file} -> {remote_path}")
            return True
        else:
            print(f"Upload failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Simple upload error: {e}")
        return False


def resumable_upload(local_file: Path, remote_path: str, section: str) -> bool:
    try:
        encoded_path = quote(remote_path, safe="/")
        drive_id = get_drive_id(section)
        endpoint = f"drives/{drive_id}/root:{encoded_path}:/createUploadSession"
        item_data = {"item": {"@microsoft.graph.conflictBehavior": "replace", "name": local_file.name}}
        response = make_graph_request("POST", endpoint, section=section, json=item_data)
        if response.status_code != 200:
            print(f"Failed to create upload session: {response.status_code} - {response.text}")
            return False
        upload_url = response.json()["uploadUrl"]
        file_content = local_file.read_bytes()
        file_size = local_file.stat().st_size
        chunk_size = 320 * 1024  # 320KB chunks
        bytes_uploaded = 0
        while bytes_uploaded < file_size:
            chunk_data = file_content[bytes_uploaded:bytes_uploaded + chunk_size]
            if not chunk_data:
                break
            chunk_end = min(bytes_uploaded + len(chunk_data) - 1, file_size - 1)
            headers = {"Content-Range": f"bytes {bytes_uploaded}-{chunk_end}/{file_size}", "Content-Length": str(len(chunk_data))}
            chunk_response = requests.put(upload_url, data=chunk_data, headers=headers)
            if chunk_response.status_code in [202, 200, 201]:
                bytes_uploaded += len(chunk_data)
                progress = (bytes_uploaded / file_size) * 100
                print(f"Upload progress: {progress:.1f}%")
            else:
                print(f"Chunk upload failed: {chunk_response.status_code} - {chunk_response.text}")
                return False
        print(f"Successfully uploaded: {local_file} -> {remote_path}")
        return True
    except Exception as e:
        print(f"Resumable upload error: {e}")
        return False


def pull_from_onedrive(remote_path: str, local_path: str, section: str) -> bool:
    if not remote_path.startswith("/"):
        remote_path = "/" + remote_path
    try:
        encoded_path = quote(remote_path, safe="/")
        drive_id = get_drive_id(section)
        endpoint = f"drives/{drive_id}/root:{encoded_path}"
        response = make_graph_request("GET", endpoint, section=section)
        if response.status_code == 404:
            print(f"File not found in OneDrive: {remote_path}")
            return False
        elif response.status_code != 200:
            print(f"Failed to get file info: {response.status_code} - {response.text}")
            return False
        file_info = response.json()
        if "folder" in file_info:
            print(f"Path is a folder, not a file: {remote_path}")
            return False
        download_url = file_info.get("@microsoft.graph.downloadUrl")
        if not download_url:
            print("No download URL available")
            return False
        local_file = Path(local_path)
        local_file.parent.mkdir(parents=True, exist_ok=True)
        download_response = requests.get(download_url, stream=True)
        download_response.raise_for_status()
        file_size = int(file_info.get("size", 0))
        bytes_downloaded = 0
        download_buffer = bytearray()
        for chunk in download_response.iter_content(chunk_size=8192):
            if chunk:
                download_buffer.extend(chunk)
                bytes_downloaded += len(chunk)
                if file_size > 0:
                    progress = (bytes_downloaded / file_size) * 100
                    print(f"Download progress: {progress:.1f}%")
        local_file.write_bytes(bytes(download_buffer))
        print(f"Successfully downloaded: {remote_path} -> {local_path}")
        return True
    except Exception as e:
        print(f"Error downloading file: {e}")
        return False


def create_remote_directory(remote_path: str, section: str) -> bool:
    if not remote_path or remote_path == "/":
        return True
    if not remote_path.startswith("/"):
        remote_path = "/" + remote_path
    try:
        encoded_path = quote(remote_path, safe="/")
        drive_id = get_drive_id(section)
        endpoint = f"drives/{drive_id}/root:{encoded_path}"
        response = make_graph_request("GET", endpoint, section=section)
        if response.status_code == 200:
            return True
        elif response.status_code != 404:
            print(f"Error checking directory: {response.status_code} - {response.text}")
            return False
        parent_dir = os.path.dirname(remote_path)
        if parent_dir and parent_dir != "/":
            if not create_remote_directory(parent_dir, section=section):
                return False
        dir_name = os.path.basename(remote_path)
        parent_encoded = quote(parent_dir if parent_dir else "/", safe="/")
        if parent_dir and parent_dir != "/":
            endpoint = f"drives/{drive_id}/root:{parent_encoded}:/children"
        else:
            endpoint = f"drives/{drive_id}/root/children"
        folder_data = {"name": dir_name, "folder": {}, "@microsoft.graph.conflictBehavior": "replace"}
        response = make_graph_request("POST", endpoint, section=section, json=folder_data)
        if response.status_code in [200, 201]:
            return True
        else:
            print(f"Failed to create directory: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Error creating directory: {e}")
        return False
