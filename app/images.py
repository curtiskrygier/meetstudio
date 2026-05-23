import logging
from app.config import gemini_client
from google.genai import types

logger = logging.getLogger("concierge")

# In-memory image cache: (prompt, model) -> bytes
image_cache: dict[tuple[str, str], bytes] = {}


async def generate_image(prompt: str, model: str = "imagen-3.0-generate-002") -> bytes | None:
    """Generate an image using the specified Imagen model. Returns raw JPEG bytes or None on failure."""
    cache_key = (prompt, model)
    if cache_key in image_cache:
        logger.info(f"[images] Cache hit for: {prompt[:80]} using {model}")
        return image_cache[cache_key]

    try:
        logger.info(f"[images] generating for prompt: {prompt[:80]} using {model}")
        response = await gemini_client.aio.models.generate_images(
            model=model,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="16:9",
            )
        )
        if response.generated_images:
            img_bytes = response.generated_images[0].image.image_bytes
            logger.info(f"[images] generated {len(img_bytes)} bytes")
            image_cache[cache_key] = img_bytes
            return img_bytes
        logger.warning("[images] no images returned")
        return None
    except Exception as e:
        logger.error(f"[images] generate failed with model {model}: {e}")
        return None


