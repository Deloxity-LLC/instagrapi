from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import sys
import os
import logging

# Add parent directory to path to import instagrapi
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from instagrapi import Client
from instagrapi.exceptions import LoginRequired, PleaseWaitFewMinutes, ChallengeRequired

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Instagrapi REST API",
    description="REST API wrapper for Instagram Private API using instagrapi",
    version="1.0.0"
)

# In-memory storage for client sessions (in production, use Redis or similar)
sessions = {}

# System client for public endpoints (auto-login on startup)
system_client = None

# Constants
SYSTEM_CLIENT_ERROR = "System client not available. Set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD environment variables."


class LoginRequest(BaseModel):
    username: str
    password: str
    session_id: Optional[str] = None


class UserInfoRequest(BaseModel):
    session_id: str
    username: str


class MediaUploadRequest(BaseModel):
    session_id: str
    caption: Optional[str] = None


@app.on_event("startup")
async def startup_event():
    """Initialize system client on startup if credentials are provided"""
    global system_client

    instagram_username = os.getenv("INSTAGRAM_USERNAME")
    instagram_password = os.getenv("INSTAGRAM_PASSWORD")

    if instagram_username and instagram_password:
        try:
            logger.info("Initializing system client for public endpoints...")
            system_client = Client()

            # Try to load existing session first
            session_file = "/app/session.json"
            if os.path.exists(session_file):
                try:
                    logger.info("Loading existing session from file...")
                    system_client.load_settings(session_file)
                    system_client.login(instagram_username, instagram_password)
                    logger.info(f"System client logged in successfully using saved session as {instagram_username}")
                except Exception as e:
                    logger.warning(f"Failed to load saved session: {str(e)}")
                    logger.info("Attempting fresh login...")
                    system_client = Client()
                    system_client.login(instagram_username, instagram_password)
                    system_client.dump_settings(session_file)
                    logger.info(f"System client logged in successfully and session saved as {instagram_username}")
            else:
                # Fresh login
                logger.info("No saved session found, performing fresh login...")
                system_client.login(instagram_username, instagram_password)
                system_client.dump_settings(session_file)
                logger.info(f"System client logged in successfully and session saved as {instagram_username}")

        except Exception as e:
            logger.error(f"Failed to login system client: {str(e)}")
            logger.warning("Public endpoints will not be available without system client")
    else:
        logger.warning("INSTAGRAM_USERNAME or INSTAGRAM_PASSWORD not set. Public endpoints will be limited.")


@app.get("/")
async def root():
    return {
        "message": "Instagrapi REST API",
        "docs": "/docs",
        "status": "running",
        "system_client_active": system_client is not None
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "system_client_active": system_client is not None
    }


@app.post("/auth/login")
async def login(request: LoginRequest):
    """Login to Instagram and create a session"""
    try:
        client = Client()

        if request.session_id and request.session_id in sessions:
            # Use existing session
            client = sessions[request.session_id]
        else:
            # New login
            client.login(request.username, request.password)

            # Generate session ID
            session_id = f"session_{len(sessions) + 1}"
            sessions[session_id] = client

            return {
                "status": "success",
                "session_id": session_id,
                "user_id": client.user_id,
                "message": "Login successful"
            }
    except LoginRequired as e:
        raise HTTPException(status_code=401, detail=f"Login required: {str(e)}")
    except ChallengeRequired as e:
        raise HTTPException(status_code=403, detail=f"Challenge required: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@app.get("/public/user/{username}")
async def get_public_user_info(username: str):
    """Get public user information by username (uses system client)"""
    try:
        if system_client is None:
            raise HTTPException(status_code=503, detail=SYSTEM_CLIENT_ERROR)

        user_id = system_client.user_id_from_username(username)
        user_info = system_client.user_info(user_id)

        return {
            "status": "success",
            "user": {
                "pk": user_info.pk,
                "username": user_info.username,
                "full_name": user_info.full_name,
                "biography": user_info.biography,
                "follower_count": user_info.follower_count,
                "following_count": user_info.following_count,
                "media_count": user_info.media_count,
                "is_private": user_info.is_private,
                "is_verified": user_info.is_verified,
                "profile_pic_url": str(user_info.profile_pic_url) if user_info.profile_pic_url else None,
                "external_url": user_info.external_url,
                "is_business": user_info.is_business
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user info: {str(e)}")


@app.post("/user/info")
async def get_user_info(request: UserInfoRequest):
    """Get user information by username (requires session)"""
    try:
        if request.session_id not in sessions:
            raise HTTPException(status_code=401, detail="Invalid session_id")

        client = sessions[request.session_id]
        user_id = client.user_id_from_username(request.username)
        user_info = client.user_info(user_id)

        return {
            "status": "success",
            "user": {
                "pk": user_info.pk,
                "username": user_info.username,
                "full_name": user_info.full_name,
                "biography": user_info.biography,
                "follower_count": user_info.follower_count,
                "following_count": user_info.following_count,
                "media_count": user_info.media_count,
                "is_private": user_info.is_private,
                "is_verified": user_info.is_verified,
                "profile_pic_url": str(user_info.profile_pic_url) if user_info.profile_pic_url else None
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user info: {str(e)}")


@app.get("/public/user/{username}/medias")
async def get_public_user_medias(username: str, amount: int = 20):
    """Get user's media posts (uses system client)"""
    try:
        if system_client is None:
            raise HTTPException(status_code=503, detail=SYSTEM_CLIENT_ERROR)

        user_id = system_client.user_id_from_username(username)
        medias = system_client.user_medias(user_id, amount)

        return {
            "status": "success",
            "count": len(medias),
            "medias": [
                {
                    "pk": media.pk,
                    "id": media.id,
                    "code": media.code,
                    "caption_text": media.caption_text,
                    "like_count": media.like_count,
                    "comment_count": media.comment_count,
                    "media_type": media.media_type,
                    "thumbnail_url": str(media.thumbnail_url) if media.thumbnail_url else None,
                    "taken_at": media.taken_at.isoformat() if media.taken_at else None
                }
                for media in medias
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get medias: {str(e)}")


@app.post("/user/{username}/medias")
async def get_user_medias(username: str, session_id: str, amount: int = 20):
    """Get user's media posts (requires session)"""
    try:
        if session_id not in sessions:
            raise HTTPException(status_code=401, detail="Invalid session_id")

        client = sessions[session_id]
        user_id = client.user_id_from_username(username)
        medias = client.user_medias(user_id, amount)

        return {
            "status": "success",
            "count": len(medias),
            "medias": [
                {
                    "pk": media.pk,
                    "id": media.id,
                    "code": media.code,
                    "caption_text": media.caption_text,
                    "like_count": media.like_count,
                    "comment_count": media.comment_count,
                    "media_type": media.media_type,
                    "thumbnail_url": str(media.thumbnail_url) if media.thumbnail_url else None
                }
                for media in medias
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get medias: {str(e)}")


@app.get("/public/media/{media_id}")
async def get_public_media_info(media_id: str):
    """Get media information by media ID or shortcode (uses system client)"""
    try:
        if system_client is None:
            raise HTTPException(status_code=503, detail=SYSTEM_CLIENT_ERROR)

        # Try to get media info (accepts both media_id and shortcode)
        try:
            media = system_client.media_info(int(media_id))
        except ValueError:
            # If not a number, try as shortcode
            media_pk = system_client.media_pk_from_code(media_id)
            media = system_client.media_info(media_pk)

        return {
            "status": "success",
            "media": {
                "pk": media.pk,
                "id": media.id,
                "code": media.code,
                "caption_text": media.caption_text,
                "like_count": media.like_count,
                "comment_count": media.comment_count,
                "media_type": media.media_type,
                "thumbnail_url": str(media.thumbnail_url) if media.thumbnail_url else None,
                "video_url": str(media.video_url) if media.video_url else None,
                "taken_at": media.taken_at.isoformat() if media.taken_at else None,
                "user": {
                    "pk": media.user.pk,
                    "username": media.user.username,
                    "full_name": media.user.full_name,
                    "profile_pic_url": str(media.user.profile_pic_url) if media.user.profile_pic_url else None
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get media info: {str(e)}")


@app.post("/photo/upload")
async def upload_photo(
    session_id: str,
    file: UploadFile = File(...),
    caption: Optional[str] = None
):
    """Upload a photo to Instagram"""
    try:
        if session_id not in sessions:
            raise HTTPException(status_code=401, detail="Invalid session_id")

        client = sessions[session_id]

        # Save uploaded file temporarily
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Upload photo
        media = client.photo_upload(temp_path, caption or "")

        # Clean up temp file
        os.remove(temp_path)

        return {
            "status": "success",
            "media": {
                "pk": media.pk,
                "id": media.id,
                "code": media.code
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Photo upload failed: {str(e)}")


@app.post("/media/{media_id}/like")
async def like_media(media_id: str, session_id: str):
    """Like a media post"""
    try:
        if session_id not in sessions:
            raise HTTPException(status_code=401, detail="Invalid session_id")

        client = sessions[session_id]
        result = client.media_like(media_id)

        return {
            "status": "success",
            "liked": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to like media: {str(e)}")


@app.post("/media/{media_id}/comment")
async def comment_media(media_id: str, session_id: str, text: str):
    """Comment on a media post"""
    try:
        if session_id not in sessions:
            raise HTTPException(status_code=401, detail="Invalid session_id")

        client = sessions[session_id]
        comment = client.media_comment(media_id, text)

        return {
            "status": "success",
            "comment": {
                "pk": comment.pk,
                "text": comment.text
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to comment: {str(e)}")


@app.delete("/session/{session_id}")
async def logout(session_id: str):
    """Logout and remove session"""
    try:
        if session_id in sessions:
            del sessions[session_id]
            return {"status": "success", "message": "Session removed"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
