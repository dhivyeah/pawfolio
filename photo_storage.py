"""Photo storage via Supabase Storage (private bucket, per-user RLS).

Was local disk (the `photos/` folder) -- that never made it into the Streamlit Cloud
deployment (gitignored, and the deployed filesystem is ephemeral on top of that anyway),
so an uploaded photo would vanish the moment the app moved off one laptop. Phase 4 also
needed this to be private per-user, not just persistent, since profiles are now
owner-scoped: the "photos" bucket is private, uploads live under {owner_id}/{uuid}.ext,
and RLS policies on storage.objects (added in db.init_db()) only let a user touch
objects under their own folder.

No signed URLs, and no public bucket: every call here downloads the raw bytes
server-side, authenticated as the current user (their own access_token from login, not
the shared anon key alone -- a signed-in user's RLS grant is what actually authorizes
the read/write). The bytes get embedded as a base64 data URI exactly the way local
files used to be, so there's never an external, fetchable photo URL for a link to leak
in the first place -- simpler than signed-URL expiry/regeneration and at least as
private, since nothing is ever exposed as a standalone fetchable resource.
"""
import os
import uuid

from dotenv import load_dotenv
from supabase import create_client
from supabase.lib.client_options import SyncClientOptions

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
BUCKET = "photos"

_MIME_BY_EXT = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def _client_for(access_token: str):
    """A fresh client per call, authenticated as the current user via their own
    access_token -- deliberately not a shared/reused client instance, since a single
    Streamlit process can be serving more than one browser session at once, and a
    shared client's auth state would bleed between users if it were reused across
    requests the way the module-level client in auth.py safely is (that one's calls
    are all stateless -- sign in/up/out don't depend on prior session state)."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise RuntimeError(
            "SUPABASE_URL / SUPABASE_ANON_KEY are not set -- needed for photo storage, "
            "same as login."
        )
    options = SyncClientOptions(headers={"Authorization": f"Bearer {access_token}"})
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY, options=options)


def upload_photo(uploaded_file, owner_id: str, access_token: str) -> str:
    """Uploads a Streamlit UploadedFile, returns its storage path (owner_id/uuid.ext).
    That path is what gets stored in profiles.photo_path -- the same role a local
    relative path used to play, just resolved through Storage now instead of disk."""
    ext = os.path.splitext(uploaded_file.name)[1].lower() or ".jpg"
    path = f"{owner_id}/{uuid.uuid4().hex}{ext}"
    mime = _MIME_BY_EXT.get(ext, "image/jpeg")
    client = _client_for(access_token)
    client.storage.from_(BUCKET).upload(
        path, uploaded_file.getvalue(), file_options={"content-type": mime}
    )
    return path


def get_photo_bytes(storage_path: str, access_token: str):
    """Raw bytes for embedding as a data URI, or None if the object doesn't exist /
    isn't accessible to this user. Never raises for a missing photo -- same "just show
    the placeholder" behavior the old local-disk lookup had for a missing file."""
    try:
        client = _client_for(access_token)
        return client.storage.from_(BUCKET).download(storage_path)
    except Exception as e:
        print(f"[photo_storage] Could not fetch {storage_path}: {e}", flush=True)
        return None


def delete_photo(storage_path: str, access_token: str):
    """Best-effort -- a failed cleanup (e.g. replacing a photo) shouldn't block the
    profile save that triggered it. Old, orphaned Storage objects piling up is the
    same already-known, already-accepted tradeoff local files had (KNOWN_ISSUES #11)."""
    try:
        client = _client_for(access_token)
        client.storage.from_(BUCKET).remove([storage_path])
    except Exception as e:
        print(f"[photo_storage] Could not delete {storage_path}: {e}", flush=True)
