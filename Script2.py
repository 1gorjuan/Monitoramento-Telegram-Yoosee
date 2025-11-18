import os
import uuid
import time
import subprocess
import logging
import signal
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)

RTSP = "rtsp://admin:83405822a@192.168.1.10:554/onvif1"
TOKEN = "8514362677:AAFKMlQYO_esLAspOsPMEzQR8p8e4WtH2rA"
CHAT = 951665102

FFMPEG_PATH = r"C:\Users\Iguinho\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0-full_build\bin\ffmpeg.exe"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

gravando = False
alerta = False
duracao_video = 1800
mensagens_enviadas = []

tempo_inicio = time.time()
running = True

def handle_signal(sig, frame):
    global running
    running = False
signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

def unique_name(ext):
    return f"{int(time.time())}_{uuid.uuid4().hex}.{ext}"

def gravar_video(duracao):
    arquivo = unique_name("mp4")
    cmd = [
        FFMPEG_PATH,
        "-rtsp_transport", "udp",
        "-i", RTSP,
        "-t", str(duracao),
        "-vcodec", "copy",
        arquivo
    ]
    subprocess.run(cmd, check=True)
    return arquivo

def tirar_foto():
    arquivo = unique_name("jpg")
    cmd = [
        FFMPEG_PATH,
        "-rtsp_transport", "udp",
        "-i", RTSP,
        "-frames:v", "1",
        arquivo
    ]
    subprocess.run(cmd, check=True)
    return arquivo

def apagar(caminho):
    try:
        if os.path.exists(caminho):
            os.remove(caminho)
    except:
        pass

COMANDOS = """
Bem-vindo ao Sistema de Monitoramento.

Comandos disponíveis:

/iniciar — Inicia gravação contínua
/parar — Para a gravação
/limpar — Apaga mensagens enviadas pelo bot
/foto — Tira foto ao vivo
/videoteste — Grava vídeo de 10s
/ultimovideo — Reenvia o último vídeo
/status — Mostra status atual
/resetar — Reseta o sistema
/autoapagamento X — Remove msgs após X minutos
/listar — Lista mensagens enviadas
/alerta_on — Ativa aviso de câmera offline
/alerta_off — Desativa aviso
/ping — Testa se o bot está online
/loop_on — Liga gravação automática
/loop_off — Desliga gravação automática
/tempo X — Muda duração dos vídeos (segundos)
"""

ultimo_video = None
autoapagamento_minutos = None

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(COMANDOS)

async def cmd_iniciar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global gravando
    if gravando:
        await update.message.reply_text("A gravação já está ativa.")
        return
    gravando = True
    await update.message.reply_text("Gravação iniciada.")
    context.application.create_task(loop_gravacao(context))

async def loop_gravacao(context):
    global gravando, ultimo_video, duracao_video
    while gravando:
        video = gravar_video(duracao_video)
        ultimo_video = video
        try:
            with open(video, "rb") as f:
                msg = await context.bot.send_video(chat_id=CHAT, video=f)
            mensagens_enviadas.append(msg.message_id)
        except Exception:
            pass
        apagar(video)
        await asyncio.sleep(1)

async def cmd_parar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global gravando
    gravando = False
    await update.message.reply_text("Gravação parada.")

async def cmd_limpar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = 0
    for msg_id in mensagens_enviadas:
        try:
            await context.bot.delete_message(chat_id=CHAT, message_id=msg_id)
            total += 1
        except:
            pass
    mensagens_enviadas.clear()
    await update.message.reply_text(f"Mensagens apagadas: {total}")

async def cmd_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    foto = tirar_foto()
    try:
        with open(foto, "rb") as f:
            msg = await context.bot.send_photo(chat_id=CHAT, photo=f)
        mensagens_enviadas.append(msg.message_id)
    except:
        pass
    apagar(foto)

async def cmd_videoteste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = gravar_video(10)
    try:
        with open(video, "rb") as f:
            msg = await context.bot.send_video(chat_id=CHAT, video=f)
        mensagens_enviadas.append(msg.message_id)
    except:
        pass
    apagar(video)

async def cmd_ultimovideo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ultimo_video
    if not ultimo_video or not os.path.exists(ultimo_video):
        await update.message.reply_text("Nenhum vídeo gravado ainda.")
        return
    try:
        with open(ultimo_video, "rb") as f:
            msg = await context.bot.send_video(chat_id=CHAT, video=f)
        mensagens_enviadas.append(msg.message_id)
    except:
        pass

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tempo_rodando = int(time.time() - tempo_inicio)
    horas = tempo_rodando // 3600
    mins = (tempo_rodando % 3600) // 60
    segs = tempo_rodando % 60
    texto = (
        f"Status do sistema:\n"
        f"Gravando: {'Sim' if gravando else 'Não'}\n"
        f"Vídeos enviados: {len(mensagens_enviadas)}\n"
        f"Tempo rodando: {horas}h {mins}m {segs}s\n"
        f"Duração atual dos vídeos: {duracao_video} segundos"
    )
    await update.message.reply_text(texto)

async def cmd_resetar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global gravando, mensagens_enviadas, ultimo_video
    gravando = False
    mensagens_enviadas.clear()
    ultimo_video = None
    await update.message.reply_text("Sistema resetado.")

async def cmd_autoapagamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global autoapagamento_minutos
    try:
        valor = int(update.message.text.split()[1])
        autoapagamento_minutos = valor
        await update.message.reply_text(f"Autoapagamento definido para {valor} minutos.")
    except:
        await update.message.reply_text("Use: /autoapagamento X")

async def cmd_listar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not mensagens_enviadas:
        await update.message.reply_text("Nenhuma mensagem enviada.")
        return
    texto = "Mensagens enviadas:\n" + "\n".join(f"ID: {m}" for m in mensagens_enviadas)
    await update.message.reply_text(texto)

async def cmd_alerta_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global alerta
    alerta = True
    await update.message.reply_text("Alerta ativado.")

async def cmd_alerta_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global alerta
    alerta = False
    await update.message.reply_text("Alerta desativado.")

async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Online.")

async def cmd_tempo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global duracao_video
    try:
        novo = int(update.message.text.split()[1])
        duracao_video = novo
        await update.message.reply_text(f"Duração alterada para {novo} segundos.")
    except:
        await update.message.reply_text("Use: /tempo X")

async def cmd_loop_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_iniciar(update, context)

async def cmd_loop_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_parar(update, context)

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("iniciar", cmd_iniciar))
    app.add_handler(CommandHandler("parar", cmd_parar))
    app.add_handler(CommandHandler("limpar", cmd_limpar))
    app.add_handler(CommandHandler("foto", cmd_foto))
    app.add_handler(CommandHandler("videoteste", cmd_videoteste))
    app.add_handler(CommandHandler("ultimovideo", cmd_ultimovideo))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("resetar", cmd_resetar))
    app.add_handler(CommandHandler("autoapagamento", cmd_autoapagamento))
    app.add_handler(CommandHandler("listar", cmd_listar))
    app.add_handler(CommandHandler("alerta_on", cmd_alerta_on))
    app.add_handler(CommandHandler("alerta_off", cmd_alerta_off))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("loop_on", cmd_loop_on))
    app.add_handler(CommandHandler("loop_off", cmd_loop_off))
    app.add_handler(CommandHandler("tempo", cmd_tempo))

    print("Bot rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()