import os
import uuid
import time
import subprocess
import asyncio
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)

# -----------------------------
# CONFIGURAÇÕES DO USUÁRIO
# -----------------------------

RTSP = ""
TOKEN = ""
CHAT = 951665102

FFMPEG_PATH = "/usr/bin/ffmpeg"   # LINUX

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

# -----------------------------
# VARIÁVEIS
# -----------------------------

gravando = False
ultimo_video = None
mensagens_enviadas = []
duracao_video = 1800
inicio_sistema = time.time()

# -----------------------------
# FUNÇÕES AUXILIARES
# -----------------------------

def unique_name(ext):
    return f"{int(time.time())}_{uuid.uuid4().hex}.{ext}"

def gravar_video(duracao):
    nome = unique_name("mp4")

    cmd = [
        FFMPEG_PATH,
        "-rtsp_transport", "tcp",
        "-i", RTSP,
        "-t", str(duracao),
        "-map", "0:v",
        "-vcodec", "copy",
        "-an",
        nome
    ]

    subprocess.run(cmd)
    return nome

def tirar_foto():
    nome = unique_name("jpg")

    cmd = [
        FFMPEG_PATH,
        "-rtsp_transport", "tcp",
        "-i", RTSP,
        "-frames:v", "1",
        "-q:v", "2",
        nome
    ]

    subprocess.run(cmd)
    return nome

def deletar(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except:
        pass

def tempo_formatado(seg):
    h = seg // 3600
    m = (seg % 3600) // 60
    s = seg % 60
    return f"{h}h {m}m {s}s"

# -----------------------------
# COMANDOS DO BOT
# -----------------------------

COMANDOS = """
Comandos disponíveis:

/iniciar — Inicia gravação contínua
/parar — Para a gravação
/limpar — Limpa mensagens
/foto — Tira foto ao vivo
/videoteste — Vídeo de 10s
/ultimovideo — Reenvia o último vídeo
/status — Status do sistema
/resetar — Reseta tudo
/listar — Lista mensagens enviadas
/ping — Teste de conexão
/tempo X — Define duração dos vídeos
"""

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(COMANDOS)

async def loop_gravacao(context):
    global gravando, ultimo_video

    while gravando:
        video = gravar_video(duracao_video)
        ultimo_video = video

        msg = await context.bot.send_video(chat_id=CHAT, video=open(video, "rb"))
        mensagens_enviadas.append(msg.message_id)

        deletar(video)
        await asyncio.sleep(1)

async def cmd_iniciar(update, context):
    global gravando

    if gravando:
        await update.message.reply_text("Já está gravando.")
        return

    gravando = True
    await update.message.reply_text("Gravação iniciada.")

    context.application.create_task(loop_gravacao(context))

async def cmd_parar(update, context):
    global gravando
    gravando = False
    await update.message.reply_text("Gravação parada.")

async def cmd_foto(update, context):
    foto = tirar_foto()
    msg = await context.bot.send_photo(chat_id=CHAT, photo=open(foto, "rb"))
    mensagens_enviadas.append(msg.message_id)
    deletar(foto)

async def cmd_videoteste(update, context):
    video = gravar_video(10)
    msg = await context.bot.send_video(chat_id=CHAT, photo=open(video, "rb"))
    mensagens_enviadas.append(msg.message_id)
    deletar(video)

async def cmd_limpar(update, context):
    apagadas = 0
    for mid in mensagens_enviadas:
        try:
            await context.bot.delete_message(chat_id=CHAT, message_id=mid)
            apagadas += 1
        except:
            pass

    mensagens_enviadas.clear()
    await update.message.reply_text(f"Mensagens apagadas: {apagadas}")

async def cmd_ultimovideo(update, context):
    if ultimo_video is None:
        await update.message.reply_text("Nenhum vídeo anterior.")
        return

    msg = await context.bot.send_video(chat_id=CHAT, video=open(ultimo_video, "rb"))
    mensagens_enviadas.append(msg.message_id)

async def cmd_status(update, context):
    uptime = tempo_formatado(int(time.time() - inicio_sistema))

    txt = f"""
Status:

Gravando: {"Sim" if gravando else "Não"}
Mensagens: {len(mensagens_enviadas)}
Uptime: {uptime}
Duração: {duracao_video}s
"""

    await update.message.reply_text(txt)

async def cmd_resetar(update, context):
    global gravando, ultimo_video, mensagens_enviadas
    gravando = False
    ultimo_video = None
    mensagens_enviadas.clear()
    await update.message.reply_text("Resetado.")

async def cmd_listar(update, context):
    if not mensagens_enviadas:
        await update.message.reply_text("Nenhuma mensagem armazenada.")
        return

    await update.message.reply_text("\n".join(str(i) for i in mensagens_enviadas))

async def cmd_ping(update, context):
    await update.message.reply_text("Online.")

async def cmd_tempo(update, context):
    global duracao_video
    try:
        novo = int(update.message.text.split()[1])
        duracao_video = novo
        await update.message.reply_text(f"Duração ajustada para {novo} segundos.")
    except:
        await update.message.reply_text("Use: /tempo 120")

# -----------------------------
# MAIN
# -----------------------------

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
    app.add_handler(CommandHandler("listar", cmd_listar))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("tempo", cmd_tempo))

    print("Bot rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()
