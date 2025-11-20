import os
import subprocess
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)

# ==============================
# CONFIGURAÇÕES GERAIS
# ==============================

RTSP = "RTPS"
TOKEN = "TOKEM"
CHAT = 951665102

DURACAO_VIDEO = 600  # 10 minutos em segundos
gravando = False
ultimo_video = None
mensagens_log = []


# ==============================
# FUNÇÃO UTILITÁRIA DE LOG
# ==============================

def registrar(msg):
    print(msg)
    mensagens_log.append(msg)
    if len(mensagens_log) > 50:
        mensagens_log.pop(0)


# ==============================
# COMANDO: FOTO
# ==============================

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "📌 *Comandos disponíveis*\n\n"
        "/iniciar — Inicia gravação contínua\n"
        "/parar — Para a gravação\n"
        "/limpar — Limpa mensagens\n"
        "/foto — Tira foto ao vivo\n"
        "/videoteste — Vídeo de 10s\n"
        "/ultimovideo — Reenvia o último vídeo\n"
        "/status — Status do sistema\n"
        "/resetar — Reseta tudo\n"
        "/listar — Lista mensagens enviadas\n"
        "/ping — Teste de conexão\n"
        "/tempo X — Define duração dos vídeos\n"
    )

    await update.message.reply_text(texto, parse_mode="Markdown")


async def cmd_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = f"foto_{int(datetime.now().timestamp())}.jpg"

    cmd = ["ffmpeg", "-y", "-rtsp_transport", "udp",
           "-i", RTSP, "-frames:v", "1", nome]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if os.path.exists(nome):
        await context.bot.send_photo(chat_id=CHAT, photo=open(nome, "rb"))
        os.remove(nome)
    else:
        await update.message.reply_text("Falha ao capturar foto.")

    registrar(f"[FOTO] {nome}")


# ==============================
# COMANDO: VIDEO TESTE (10s)
# ==============================

async def cmd_videoteste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = f"teste_{int(datetime.now().timestamp())}.mp4"

    cmd = ["ffmpeg", "-y",
           "-rtsp_transport", "udp",
           "-i", RTSP,
           "-t", "10",
           "-c", "copy",
           nome]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if os.path.exists(nome):
        await context.bot.send_video(chat_id=CHAT, video=open(nome, "rb"))
        os.remove(nome)
    else:
        await update.message.reply_text("Falha ao gerar vídeo teste.")

    registrar(f"[VIDEO TESTE] {nome}")


# ==============================
# FUNÇÃO DE GRAVAÇÃO CONTÍNUA
# ==============================

async def gravar_continuo(app):
    global gravando, ultimo_video

    while gravando:
        nome = f"rec_{int(datetime.now().timestamp())}.mp4"
        ultimo_video = nome

        cmd = ["ffmpeg", "-y",
               "-rtsp_transport", "udp",
               "-i", RTSP,
               "-t", str(DURACAO_VIDEO),
               "-c", "copy",
               nome]

        registrar(f"[GRAVANDO] {nome}")

        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if not gravando:
            return

        if os.path.exists(nome):
            try:
                await app.bot.send_video(chat_id=CHAT, video=open(nome, "rb"))
            except:
                registrar("[ERRO] Falha ao enviar vídeo.")
            finally:
                if os.path.exists(nome):
                    os.remove(nome)


# ==============================
# COMANDO: INICIAR
# ==============================

async def cmd_iniciar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global gravando

    if gravando:
        await update.message.reply_text("Já está gravando.")
        return

    gravando = True
    await update.message.reply_text("Gravação contínua iniciada.")

    asyncio.create_task(gravar_continuo(context.application))  # inicia em paralelo

    registrar("[SISTEMA] Gravação iniciada")


# ==============================
# COMANDO: PARAR
# ==============================

async def cmd_parar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global gravando
    gravando = False

    await update.message.reply_text("Gravação parada.")
    registrar("[SISTEMA] Gravação parada")


# ==============================
# COMANDO: ULTIMO VÍDEO
# ==============================

async def cmd_ultimovideo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ultimo_video

    if ultimo_video is None or not os.path.exists(ultimo_video):
        await update.message.reply_text("Nenhum vídeo disponível.")
        return

    await update.message.reply_text("Enviando o último vídeo.")
    await update.message.reply_video(video=open(ultimo_video, "rb"))

    registrar(f"[ENVIO] {ultimo_video}")


# ==============================
# COMANDO: STATUS
# ==============================

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = "Gravando" if gravando else "Parado"
    await update.message.reply_text(f"Status: {status}")
    registrar("[STATUS] Solicitado")


# ==============================
# COMANDO: RESETAR
# ==============================

async def cmd_resetar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global gravando, ultimo_video, mensagens_log

    gravando = False
    ultimo_video = None
    mensagens_log = []

    await update.message.reply_text("Sistema resetado.")
    registrar("[SISTEMA] Reset")


# ==============================
# COMANDO: LISTAR
# ==============================

async def cmd_listar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not mensagens_log:
        await update.message.reply_text("Não há logs.")
        return

    texto = "\n".join(mensagens_log[-20:])
    await update.message.reply_text(f"Últimas mensagens:\n\n{texto}")


# ==============================
# COMANDO: LIMPAR
# ==============================

async def cmd_limpar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=CHAT, text="/limpar comando executado.")
    registrar("[COMANDO] limpar")


# ==============================
# COMANDO: PING
# ==============================

async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pong!")
    registrar("[PING]")


# ==============================
# COMANDO: TEMPO X
# ==============================

async def cmd_tempo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global DURACAO_VIDEO

    try:
        X = int(update.message.text.split(" ")[1])
        DURACAO_VIDEO = X * 60
        await update.message.reply_text(f"Duração do vídeo ajustada para {X} minutos.")
        registrar(f"[TEMPO] novo = {DURACAO_VIDEO}s")

    except:
        await update.message.reply_text("Uso correto: /tempo 5   (para 5 minutos)")


# ==============================
# INÍCIO DO SISTEMA
# ==============================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

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
    app.add_handler(CommandHandler("help", cmd_help))


    app.run_polling()


if __name__ == "__main__":
    main()
