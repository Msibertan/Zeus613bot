import asyncio
import logging
import os
import httpx
import json
from config import NANO_BANANA_API_KEY, BLURIT_CLIENT_ID, BLURIT_SECRET_ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_GENERATE_URL = "https://api.nanobananaapi.ai/api/v1/nanobanana/generate-pro"
API_RECORD_INFO_URL = "https://api.nanobananaapi.ai/api/v1/nanobanana/record-info"

async def generate_image(image_url: str, prompt: str, aspect_ratio: str | None = None, image_strength: float = 0.75) -> str:
    """Sends a request to Nano Banana API and polls for the result."""
    headers = {
        "Authorization": f"Bearer {NANO_BANANA_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "Nano Banana Pro",
        "taskType": "image-to-image",
        "imageUrls": [image_url],
        "prompt": prompt,
        "resolution": "2K",
        "imageStrength": image_strength
    }
    if aspect_ratio:
        payload["aspectRatio"] = aspect_ratio

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(API_GENERATE_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            data_obj = data.get("data")
            if not data_obj:
                logger.error(f"API rejected the request or data is missing. Full Response: {data}")
                return ""
            
            task_id = data_obj.get("taskId")
            if not task_id:
                logger.error(f"Failed to get taskId. Response: {data}")
                return ""
                
            logger.info(f"Task started with taskId: {task_id}")
            
        except httpx.HTTPError as e:
            logger.error(f"API HTTP Error during POST: {e}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error during POST: {e}")
            return ""

        max_retries = 24
        for i in range(max_retries):
            await asyncio.sleep(10)
            try:
                poll_response = await client.get(f"{API_RECORD_INFO_URL}?taskId={task_id}", headers=headers)
                poll_response.raise_for_status()
                poll_data = poll_response.json()
                
                data_obj = poll_data.get("data", {})
                success_flag = data_obj.get("successFlag")
                
                if success_flag == 1:
                    response_obj = data_obj.get("response", {})
                    result_url = ""
                    if isinstance(response_obj, dict):
                        result_url = response_obj.get("resultImageUrl")
                    elif isinstance(response_obj, str):
                        try:
                            parsed_response = json.loads(response_obj)
                            result_url = parsed_response.get("resultImageUrl")
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse response JSON string")
                    
                    if result_url:
                        logger.info(f"Task {task_id} completed successfully.")
                        return result_url
                    else:
                        logger.error(f"Task {task_id} completed but resultImageUrl is missing.")
                        return ""
                elif success_flag == 3:
                    logger.error(f"Task {task_id} failed with successFlag=3. Server Response: {poll_data}")
                    return ""
                
            except httpx.HTTPError as e:
                logger.error(f"API HTTP Error during GET polling: {e}")
            except Exception as e:
                logger.error(f"Unexpected error during GET polling: {e}")

        logger.error(f"Timeout waiting for task {task_id} to complete.")
        return ""

async def process_blurit_video(file_path: str) -> str:
    """Authenticates and sends a video to Blurit (Wassa) API for processing, then polls for the result."""
    login_url = "https://api.services.wassa.io/login"
    task_url = "https://api.services.wassa.io/innovation-service/anonymization"
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            auth_payload = {
                "clientId": BLURIT_CLIENT_ID,
                "secretId": BLURIT_SECRET_ID
            }
            auth_response = await client.post(login_url, json=auth_payload)
            auth_response.raise_for_status()
            token_data = auth_response.json()
            access_token = token_data.get("access_token") or token_data.get("token")
            
            if not access_token:
                logger.error("Failed to get access_token from Blurit API.")
                return ""
            
            headers = {"Authorization": f"Bearer {access_token}"}
            
            with open(file_path, "rb") as f:
                files = {"input_media": f}
                data = {
                    "activation_plates_blur": "true",
                    "activation_faces_blur": "false",
                    "blur_type": '{"anonymization_type": "blur"}'
                }
                response = await client.post(task_url, files=files, data=data, headers=headers)
            
            response.raise_for_status()
            task_id = response.json().get("anonymization_job_id")
            
            if not task_id:
                logger.error("Failed to get anonymization_job_id from API.")
                return ""
            
            max_retries = 60
            poll_url = f"{task_url}?anonymization_job_id={task_id}"
            
            for i in range(max_retries):
                await asyncio.sleep(10)
                poll_response = await client.get(poll_url, headers=headers)
                poll_response.raise_for_status()
                
                poll_data = poll_response.json()
                status = poll_data.get("status")
                
                if status == "Succeeded":
                    result_url = poll_data.get("output_media")
                    if result_url:
                        result_file_path = f"temp/result_{task_id}.mp4"
                        async with client.stream("GET", result_url, headers=headers) as r:
                            r.raise_for_status()
                            with open(result_file_path, "wb") as f_out:
                                async for chunk in r.aiter_bytes():
                                    f_out.write(chunk)
                        return result_file_path
                    return ""
                elif status in ["Failed", "Error"]:
                    return ""
                
            return ""
    except Exception as e:
        logger.error(f"Error in process_blurit_video: {e}")
        return ""

async def make_video_note(input_path: str, bg_type: str = "standard") -> str:
    """Creates a 60s max, 1:1, 640x640 Telegram Video Note with optional background."""
    try:
        from moviepy import VideoFileClip
        import moviepy.video.fx as vfx
        from moviepy import ColorClip, CompositeVideoClip
        from moviepy.video.tools.drawing import circle
        
        output_path = f"temp/note_{os.path.basename(input_path)}"
        clip = VideoFileClip(input_path)
        
        if clip.duration > 60:
            clip = clip.subclipped(0, 60)
            
        w, h = clip.size
        min_side = min(w, h)
        x_center = w / 2
        y_center = h / 2
        
        clip = clip.with_effects([
            vfx.Crop(width=min_side, height=min_side, x_center=x_center, y_center=y_center),
            vfx.Resize(width=640, height=640)
        ])
        
        if bg_type in ["white", "black"]:
            mask_np = circle(screensize=(640, 640), center=(320, 320), radius=320, color=1.0, bg_color=0.0, blur=2)
            from moviepy import ImageClip
            mask_clip = ImageClip(mask_np, is_mask=True).with_duration(clip.duration)
            clip = clip.with_mask(mask_clip)
            
            bg_color = (255, 255, 255) if bg_type == "white" else (0, 0, 0)
            bg_clip = ColorClip(size=(640, 640), color=bg_color, duration=clip.duration)
            clip = CompositeVideoClip([bg_clip, clip.with_position("center")])
        
        clip.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac",
            logger=None
        )
        clip.close()
        return output_path
    except Exception as e:
        logger.error(f"Error in make_video_note: {e}", exc_info=True)
        return None
