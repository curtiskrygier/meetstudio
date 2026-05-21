import logging
from app.config import gemini_client
from google.genai import types

logger = logging.getLogger("concierge")


async def generate_image(prompt: str) -> bytes | None:
    """Generate an image using Imagen 4 Fast. Returns raw JPEG bytes or None on failure."""
    try:
        logger.info(f"[images] generating for prompt: {prompt[:80]}")
        response = await gemini_client.aio.models.generate_images(
            model="imagen-4.0-fast-generate-001",
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="16:9",
            )
        )
        if response.generated_images:
            img_bytes = response.generated_images[0].image.image_bytes
            logger.info(f"[images] generated {len(img_bytes)} bytes")
            return img_bytes
        logger.warning("[images] no images returned")
        return None
    except Exception as e:
        logger.error(f"[images] generate failed: {e}")
        return None
