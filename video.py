import requests
import aria2p
from datetime import datetime
from status import format_progress_bar
import asyncio
import os, time
import logging

# Initialize Aria2 API
aria2 = aria2p.API(
    aria2p.Client(
        host="http://localhost",
        port=6800,
        secret=""
    )
)

async def download_video(url, reply_msg, user_mention, user_id):
    """Fetch video details and download using Aria2."""
    
    # Fetch video details from the API
    response = requests.get(f"https://teraboxapi-phi.vercel.app/api?url={url}")
    response.raise_for_status()
    data = response.json()

    # Extract relevant details
    extracted_info = data["Extracted Info"][0]  # First item in list
    fast_download_link = extracted_info["Direct Download Link"]
    thumbnail_url = extracted_info["Thumbnails"]["360x270"]  # Best quality thumbnail
    video_title = extracted_info["Title"]

    # Start downloading
    download = aria2.add_uris([fast_download_link])
    start_time = datetime.now()

    while not download.is_complete:
        download.update()
        percentage = download.progress
        done = download.completed_length
        total_size = download.total_length
        speed = download.download_speed
        eta = download.eta
        elapsed_time_seconds = (datetime.now() - start_time).total_seconds()
        
        # Generate progress bar
        progress_text = format_progress_bar(
            filename=video_title,
            percentage=percentage,
            done=done,
            total_size=total_size,
            status="Downloading",
            eta=eta,
            speed=speed,
            elapsed=elapsed_time_seconds,
            user_mention=user_mention,
            user_id=user_id,
            aria2p_gid=download.gid
        )
        await reply_msg.edit_text(progress_text)
        await asyncio.sleep(2)

    if download.is_complete:
        file_path = download.files[0].path

        # Download and save the thumbnail
        thumbnail_path = "thumbnail.jpg"
        thumbnail_response = requests.get(thumbnail_url)
        with open(thumbnail_path, "wb") as thumb_file:
            thumb_file.write(thumbnail_response.content)

        await reply_msg.edit_text("ᴜᴘʟᴏᴀᴅɪɴɢ...")

        return file_path, thumbnail_path, video_title
    else:
        raise Exception("Download failed")

async def upload_video(client, file_path, thumbnail_path, video_title, reply_msg, collection_channel_id, user_mention, user_id, message):
    """Upload video to Telegram."""
    
    file_size = os.path.getsize(file_path)
    uploaded = 0
    start_time = datetime.now()
    last_update_time = time.time()

    async def progress(current, total):
        nonlocal uploaded, last_update_time
        uploaded = current
        percentage = (current / total) * 100
        elapsed_time_seconds = (datetime.now() - start_time).total_seconds()
        
        if time.time() - last_update_time > 2:
            progress_text = format_progress_bar(
                filename=video_title,
                percentage=percentage,
                done=current,
                total_size=total,
                status="Uploading",
                eta=(total - current) / (current / elapsed_time_seconds) if current > 0 else 0,
                speed=current / elapsed_time_seconds if current > 0 else 0,
                elapsed=elapsed_time_seconds,
                user_mention=user_mention,
                user_id=user_id,
                aria2p_gid=""
            )
            try:
                await reply_msg.edit_text(progress_text)
                last_update_time = time.time()
            except Exception as e:
                logging.warning(f"Error updating progress message: {e}")

    with open(file_path, 'rb') as file:
        collection_message = await client.send_video(
            chat_id=collection_channel_id,
            video=file,
            caption=f"✨ {video_title}\n👤 ʟᴇᴇᴄʜᴇᴅ ʙʏ : {user_mention}\n📥 ᴜsᴇʀ ʟɪɴᴋ: tg://user?id={user_id}",
            thumb=thumbnail_path,
            progress=progress
        )
        await client.copy_message(
            chat_id=message.chat.id,
            from_chat_id=collection_channel_id,
            message_id=collection_message.id
        )
        await asyncio.sleep(1)
        await message.delete()
        await message.reply_sticker("CAACAgIAAxkBAAEZdwRmJhCNfFRnXwR_lVKU1L9F3qzbtAAC4gUAAj-VzApzZV-v3phk4DQE")

    await reply_msg.delete()

    os.remove(file_path)
    os.remove(thumbnail_path)
    return collection_message.id
