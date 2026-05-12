import httpx
import re
import asyncio
import json
from datetime import datetime, timezone, timedelta
from app.config import meeting_name_cache, meeting_folder_cache
from app.utils import svg_to_png

async def get_calendar_meeting_name(space_id: str, access_token: str) -> str:
    """Return the Calendar event title for this Meet space, '' if not found."""
    if space_id in meeting_name_cache:
        return meeting_name_cache[space_id]
    try:
        bare = re.sub(r'^spaces[_/]', '', space_id)
        now = datetime.now(timezone.utc)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                params={
                    "singleEvents": "true",
                    "timeMin": (now - timedelta(hours=3)).isoformat(),
                    "timeMax": (now + timedelta(hours=3)).isoformat(),
                    "fields": "items(summary,hangoutLink,conferenceData/conferenceId)",
                    "maxResults": "50",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if resp.status_code != 200:
            print(f"[calendar] {resp.status_code}: {resp.text[:200]}", flush=True)
            return ""
        for event in resp.json().get("items", []):
            hangout = event.get("hangoutLink", "")
            conf_id = (event.get("conferenceData") or {}).get("conferenceId", "")
            if bare and (bare in hangout or bare in conf_id):
                name = event.get("summary", "").strip()
                print(f"[calendar] matched '{name}' for {bare}", flush=True)
                meeting_name_cache[space_id] = name
                return name
        print(f"[calendar] no event matched for {bare}", flush=True)
    except Exception as e:
        print(f"[calendar] {type(e).__name__}: {e}", flush=True)
    return ""

async def _drive_get_or_create_folder(name: str, parent: str, access_token: str) -> str | None:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        q = f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and '{parent}' in parents and trashed = false"
        resp = await client.get(
            "https://www.googleapis.com/drive/v3/files",
            params={
                "q": q,
                "fields": "files(id)",
                "spaces": "drive",
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true"
            },
            headers=headers,
        )
        if resp.status_code == 200:
            files = resp.json().get("files", [])
            if files:
                return files[0]["id"]
        
        # Create it
        resp = await client.post(
            "https://www.googleapis.com/drive/v3/files",
            params={"supportsAllDrives": "true"},
            json={
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent] if parent != "root" else []
            },
            headers=headers,
        )
        if resp.status_code in (200, 201):
            return resp.json()["id"]
        else:
            print(f"[drive] folder create failed: {resp.status_code} {resp.text}", flush=True)
    return None

async def get_or_create_meeting_folder(space_id: str, access_token: str, meeting_name: str = "") -> str | None:
    """Return the Drive folder ID for this meeting, creating it if needed."""
    if space_id in meeting_folder_cache and not meeting_name:
        return meeting_folder_cache[space_id]

    if meeting_name:
        folder_name = re.sub(r'[^\w\s\-]', '', meeting_name).strip()[:50] or "Test Meeting"
    else:
        calendar_name = await get_calendar_meeting_name(space_id, access_token)
        bare = re.sub(r'^spaces[_/]', '', space_id) or "meeting"
        folder_name = re.sub(r'[^\w\s\-]', '', calendar_name).strip()[:50] if calendar_name else bare

    recordings_id = await _drive_get_or_create_folder("Meet Recordings", "root", access_token)
    if not recordings_id:
        return None
    folder_id = await _drive_get_or_create_folder(folder_name, recordings_id, access_token)
    if folder_id and not meeting_name:
        meeting_folder_cache[space_id] = folder_id

    print(f"[drive] using folder '{folder_name}' id={folder_id}", flush=True)
    return folder_id

async def save_diagram_to_drive(svg_bytes: bytes, title: str, space_id: str, access_token: str, meeting_name: str = "") -> str | None:
    folder_id = await get_or_create_meeting_folder(space_id, access_token, meeting_name=meeting_name)
    
    # Convert to PNG for high-quality preview in Drive
    png = await asyncio.get_event_loop().run_in_executor(None, svg_to_png, svg_bytes)
    if not png:
        print("[drive] PNG conversion failed, cannot save to Drive", flush=True)
        return None

    filename = f"{title}.png"
    boundary = "-------314159265358979323846"
    metadata = {
        "name": filename,
        "parents": [folder_id] if folder_id else []
    }
    
    body = (
        f"--{boundary}\n"
        f"Content-Type: application/json; charset=UTF-8\n\n"
        f"{json.dumps(metadata)}\n"
        f"--{boundary}\n"
        f"Content-Type: image/png\n\n"
    ).encode("utf-8") + png + f"\n--{boundary}--".encode("utf-8")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
            params={"supportsAllDrives": "true"},
            content=body,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": f"multipart/related; boundary={boundary}",
            },
        )
    if resp.status_code in (200, 201):
        file_id = resp.json().get("id")
        print(f"[drive] saved '{filename}' id={file_id}", flush=True)
        return file_id
    else:
        print(f"[drive] upload failed: {resp.status_code} {resp.text}", flush=True)
        return None

async def save_doc_shortcut_to_drive(doc_url: str, doc_title: str, space_id: str, access_token: str):
    """Create a Drive shortcut to a workspace doc in the meeting folder."""
    if not access_token or not space_id:
        return
    file_id_match = re.search(r'/d/([a-zA-Z0-9_-]+)', doc_url)
    if not file_id_match:
        return
    file_id = file_id_match.group(1)
    try:
        meeting_folder_id = await get_or_create_meeting_folder(space_id, access_token)
        if not meeting_folder_id:
            return
        safe_name = re.sub(r'[^\w\s-]', '', doc_title or "Document").strip()[:40] or "Document"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://www.googleapis.com/drive/v3/files",
                params={"supportsAllDrives": "true"},
                json={
                    "name": safe_name,
                    "mimeType": "application/vnd.google-apps.shortcut",
                    "parents": [meeting_folder_id],
                    "shortcutDetails": {"targetId": file_id},
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if resp.status_code in (200, 201):
            print(f"[drive] shortcut '{safe_name}' created", flush=True)
        else:
            print(f"[drive] shortcut {resp.status_code}: {resp.text[:200]}", flush=True)
    except Exception as e:
        print(f"[drive] shortcut {type(e).__name__}: {e}", flush=True)

async def fetch_meeting_chat(space_id: str, access_token: str) -> str:
    if not space_id or not access_token:
        return ""
    bare_id = re.sub(r'^spaces[_/]', '', space_id).strip()
    if not bare_id: return ""
    full_space_id = f"spaces/{bare_id}"
    try:
        url = f"https://chat.googleapis.com/v1/{full_space_id}/messages?pageSize=100&orderBy=createTime+asc"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})
        if resp.status_code != 200:
            print(f"[chat] API {resp.status_code} for {full_space_id}: {resp.text[:200]}", flush=True)
            return ""
        messages = []
        for m in resp.json().get("messages", []):
            sender = m.get("sender", {}).get("displayName", "Unknown")
            text = m.get("text", m.get("formattedText", "")).strip()
            if text:
                messages.append(f"{sender}: {text}")
        result = "\n".join(messages)
        print(f"[chat] {len(messages)} messages ({len(result)} chars)", flush=True)
        return result
    except Exception as e:
        print(f"[chat] error: {type(e).__name__}: {e}", flush=True)
        return ""
