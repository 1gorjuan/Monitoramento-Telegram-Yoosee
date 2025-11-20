import cv2
import time
import asyncio
import subprocess
import numpy as np
from telegram import Bot
import sys
import uuid
import logging
import signal
import os

RTSP = ""
TOKEN = ""
CHAT = 951665102

FFMPEG_PATH = r"C:\Users\Iguinho\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0-full_build\bin\ffmpeg.exe"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

bot = Bot(TOKEN)

running = True

def handle_signal(sig, frame):
    global running
    running = False
    logging.info("Encerrando o script com segurança")

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

def open_ffmpeg():
    cmd = [
        FFMPEG_PATH,
        "-rtsp_transport", "udp",
        "-i", RTSP,
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-"
    ]
    try:
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10**8)
    except:
        return None

def read_frame(proc, width=640, height=360, timeout=1.3):
    size = width * height * 3
    start = time.time()
    data = bytearray()
    while len(data) < size:
        if time.time() - start > timeout:
            return None
        part = proc.stdout.read(size - len(data))
        if not part:
            return None
        data.extend(part)
    return np.frombuffer(data, dtype=np.uint8).reshape((height, width, 3))

def unique_name(ext):
    return f"{int(time.time())}_{uuid.uuid4().hex}.{ext}"

def record_video():
    name = unique_name("mp4")
    cmd = [
        FFMPEG_PATH,
        "-rtsp_transport", "udp",
        "-i", RTSP,
        "-t", "15",
        "-vcodec", "copy",
        name
    ]
    subprocess.run(cmd)
    return name

def capture_photo():
    name = unique_name("jpg")
    cmd = [
        FFMPEG_PATH,
        "-rtsp_transport", "udp",
        "-i", RTSP,
        "-frames:v", "1",
        name
    ]
    subprocess.run(cmd)
    return name

def delete_file(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except:
        pass

async def main():
    await bot.send_message(chat_id=CHAT, text="O bot foi iniciado")
    init_photo = capture_photo()
    with open(init_photo, "rb") as f:
        await bot.send_photo(chat_id=CHAT, photo=f)
    delete_file(init_photo)

    ffmpeg = open_ffmpeg()
    if ffmpeg is None:
        sys.exit(1)

    background = None
    sensitivity = 32
    cooldown = 18
    last_send = 0
    fail_count = 0
    fail_limit = 15

    while running:
        try:
            frame = read_frame(ffmpeg)
            if frame is None:
                fail_count += 1
                ffmpeg.kill()
                ffmpeg.wait()
                ffmpeg = open_ffmpeg()
                if fail_count >= fail_limit:
                    break
                continue

            fail_count = 0

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            if background is None:
                background = gray.astype("float")
                continue

            cv2.accumulateWeighted(gray, background, 0.025)
            bg = cv2.convertScaleAbs(background)

            delta = cv2.absdiff(bg, gray)
            _, thresh = cv2.threshold(delta, sensitivity, 255, cv2.THRESH_BINARY)
            thresh = cv2.dilate(thresh, None, iterations=2)

            h, w = gray.shape
            x1, x2 = int(w * 0.25), int(w * 0.75)
            y1, y2 = int(h * 0.25), int(h * 0.75)

            zone = thresh[y1:y2, x1:x2]

            contours, _ = cv2.findContours(zone, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            detected = False

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > 2800:
                    detected = True
                    break

            now = time.time()

            if detected and now - last_send > cooldown:
                last_send = now

                video = record_video()
                with open(video, "rb") as v:
                    await bot.send_video(chat_id=CHAT, video=v)
                delete_file(video)

                await asyncio.sleep(2)

                photo = capture_photo()
                with open(photo, "rb") as f:
                    await bot.send_photo(chat_id=CHAT, photo=f)
                delete_file(photo)

            await asyncio.sleep(0.05)

        except Exception as e:
            logging.error(e)
            await asyncio.sleep(1)

    logging.info("Script finalizado")

if __name__ == "__main__":
    asyncio.run(main())
