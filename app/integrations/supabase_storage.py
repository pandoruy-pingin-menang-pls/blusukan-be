import uuid

from supabase import Client, create_client

from app.core.config import settings
from app.core.logging import logger


class SupabaseStorage:
    def __init__(self):
        self.url = settings.SUPABASE_URL
        # Using Service Role Key to bypass RLS for server-side uploads
        self.key = settings.SUPABASE_SERVICE_ROLE_KEY
        if self.url and self.key:
            self.client: Client = create_client(self.url, self.key)
        else:
            self.client = None
            logger.warning("Supabase URL or Key is not set. Uploads will be mocked.")

        self.bucket_menu = settings.SUPABASE_STORAGE_BUCKET_MENU

    async def upload_menu_image(self, file_bytes: bytes, mime_type: str, merchant_id: str) -> str:
        """
        Uploads a menu image to Supabase Storage and returns the public URL.
        """
        if not self.client:
            logger.info("Mocking Supabase Storage upload")
            return f"https://mocked-supabase.com/storage/{self.bucket_menu}/{merchant_id}/mocked-image.jpg"

        file_extension = "jpg"
        if mime_type == "image/png":
            file_extension = "png"

        # Path: {merchant_id}/{uuid}.{ext}
        file_path = f"{merchant_id}/{uuid.uuid4()}.{file_extension}"

        try:
            # We use synchronous upload for simplicity, but it runs fast enough for backend
            self.client.storage.from_(self.bucket_menu).upload(
                file=file_bytes,
                path=file_path,
                file_options={"content-type": mime_type}
            )

            # Get public URL
            public_url = self.client.storage.from_(self.bucket_menu).get_public_url(file_path)
            return public_url
        except Exception as e:
            logger.error(f"Failed to upload to Supabase Storage: {str(e)}")
            raise

supabase_storage = SupabaseStorage()
