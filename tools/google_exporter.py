import os
import time
import datetime
from typing import List, Optional

import httplib2
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_httplib2 import AuthorizedHttp

# ──────────────────────────────
# CONFIG
# ──────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
_DEFAULT_TIMEOUT = 120  # seconds

# Email to share the folder with
SHARE_WITH_EMAIL = "satinsiders@gmail.com"
# Cached folder ID once created or found
EXPORT_FOLDER_ID: Optional[str] = None


def _get_creds():
    key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not key_path:
        local = os.path.join(os.path.dirname(__file__), "google_sa.json")
        if os.path.exists(local):
            key_path = local

    if not key_path or not os.path.isfile(key_path):
        raise RuntimeError(
            f"Service account JSON not found. Checked: "
            f"{os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}, "
            f"{local if 'local' in locals() else 'N/A'}"
        )

    return service_account.Credentials.from_service_account_file(
        key_path, scopes=SCOPES
    )


def _build_service(api_name: str, version: str):
    creds = _get_creds()
    http = httplib2.Http(timeout=_DEFAULT_TIMEOUT)
    authed_http = AuthorizedHttp(creds, http=http)
    return build(api_name, version, http=authed_http)


def _execute_request(request, retries: int = 3, delay: float = 2.0):
    for attempt in range(1, retries + 1):
        try:
            return request.execute()
        except HttpError:
            if attempt == retries:
                raise
            time.sleep(delay * (2 ** (attempt - 1)))


def ensure_export_folder() -> str:
    """
    Create a Drive folder named with the current date/time,
    share it with SHARE_WITH_EMAIL, and return its folder ID.
    """
    global EXPORT_FOLDER_ID
    if EXPORT_FOLDER_ID:
        return EXPORT_FOLDER_ID

    drive = _build_service("drive", "v3")
    # Generate folder name based on creation timestamp
    folder_name = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Look for an existing folder with the same timestamped name (unlikely)
    list_req = drive.files().list(
        q=(
            f"name = '{folder_name}' "
            "and mimeType = 'application/vnd.google-apps.folder' "
            "and trashed = false"
        ),
        fields="files(id,name)"
    )
    resp = _execute_request(list_req)
    files = resp.get("files", [])

    if files:
        EXPORT_FOLDER_ID = files[0]["id"]
    else:
        # Create a new timestamped folder
        metadata = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
        create_req = drive.files().create(body=metadata, fields="id")
        folder = _execute_request(create_req)
        EXPORT_FOLDER_ID = folder["id"]

        # Share with the specified email
        perm_req = drive.permissions().create(
            fileId=EXPORT_FOLDER_ID,
            body={
                "type": "user",
                "role": "writer",
                "emailAddress": SHARE_WITH_EMAIL
            },
            fields="id"
        )
        _execute_request(perm_req)

    return EXPORT_FOLDER_ID


def _move_file_to_folder(file_id: str):
    # Ensure the export folder exists and get its ID
    folder_id = ensure_export_folder()
    drive = _build_service("drive", "v3")
    req = drive.files().update(
        fileId=file_id,
        addParents=folder_id,
        removeParents="root"
    )
    _execute_request(req)


def create_lesson_doc(content: List[dict], title: str) -> str:
    """
    content: list of elements with text and optional style markup.
    """
    docs = _build_service("docs", "v1")

    # Step 1: create the document
    create_req = docs.documents().create(body={"title": title})
    file = _execute_request(create_req)
    doc_id = file["documentId"]

    # Step 2: build batchUpdate requests
    requests = []
    index = 1

    for el in content:
        text = el.get("text", "") + "\n"
        text_len = len(text)

        # Insert the text
        requests.append({
            "insertText": {
                "location": {"index": index},
                "text": text
            }
        })

        # unified double-spacing + optional named style
        paragraph_style = {"lineSpacing": 200}
        fields = ["lineSpacing"]

        if el.get("style"):
            paragraph_style["namedStyleType"] = el["style"]
            fields.append("namedStyleType")

        requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": index, "endIndex": index + text_len},
                "paragraphStyle": paragraph_style,
                "fields": ",".join(fields)
            }
        })

        # Apply font/size via weightedFontFamily
        if el.get("style") == "HEADING_1":
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": index, "endIndex": index + text_len},
                    "textStyle": {
                        "weightedFontFamily": {"fontFamily": "Georgia", "weight": 400},
                        "fontSize": {"magnitude": 24, "unit": "PT"},
                        "bold": True
                    },
                    "fields": "weightedFontFamily,fontSize,bold"
                }
            })
        elif el.get("style") == "HEADING_2":
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": index, "endIndex": index + text_len},
                    "textStyle": {
                        "weightedFontFamily": {"fontFamily": "Georgia", "weight": 400},
                        "fontSize": {"magnitude": 18, "unit": "PT"},
                        "bold": True
                    },
                    "fields": "weightedFontFamily,fontSize,bold"
                }
            })
        else:
            # Body text in Georgia 14pt
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": index, "endIndex": index + text_len},
                    "textStyle": {
                        "weightedFontFamily": {"fontFamily": "Georgia", "weight": 400},
                        "fontSize": {"magnitude": 14, "unit": "PT"}
                    },
                    "fields": "weightedFontFamily,fontSize"
                }
            })

        # Apply inline bold/italic/underline
        text_style = {}
        if el.get("bold"):
            text_style["bold"] = True
        if el.get("italic"):
            text_style["italic"] = True
        if el.get("underline"):
            text_style["underline"] = True

        if text_style:
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": index, "endIndex": index + text_len},
                    "textStyle": text_style,
                    "fields": ",".join(text_style.keys())
                }
            })

        index += text_len

    # Step 3: send the batchUpdate
    batch_req = docs.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests}
    )
    _execute_request(batch_req)

    # Step 4: move to folder
    _move_file_to_folder(doc_id)

    return f"https://docs.google.com/document/d/{doc_id}/edit"


def create_mcq_sheet(rows: List[List[str]], title: str) -> str:
    sheets = _build_service("sheets", "v4")
    create_req = sheets.spreadsheets().create(body={"properties": {"title": title}})
    sheet = _execute_request(create_req)
    sheet_id = sheet["spreadsheetId"]

    update_req = sheets.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range="A1",
        valueInputOption="RAW",
        body={"values": rows}
    )
    _execute_request(update_req)

    _move_file_to_folder(sheet_id)
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
