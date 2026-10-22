import os
import threading
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import yt_dlp

# --- Web Server to Keep the Bot Alive ---
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running 24/7!"

def run_flask():
    # Render provides a dynamic PORT environment variable
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)
# ----------------------------------------

# Temporary storage for users' links
user_links = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      'Send me a YouTube video link, and I will let you choose the quality!'
  )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
  url = update.message.text
  if 'youtube.com' not in url and 'youtu.be' not in url:
    await update.message.reply_text('Please send a valid YouTube link.')
    return

  user_id = update.message.from_user.id
  user_links[user_id] = url

  keyboard = [
      [
          InlineKeyboardButton(
              '1080p (Best HD)',
              callback_data='bestvideo[height<=1080]+bestaudio',
          ),
          InlineKeyboardButton(
              '720p (HD)', callback_data='bestvideo[height<=720]+bestaudio'
          ),
      ],
      [
          InlineKeyboardButton(
              '480p (SD)', callback_data='bestvideo[height<=480]+bestaudio'
          ),
          InlineKeyboardButton(
              '360p (Low)', callback_data='bestvideo[height<=360]+bestaudio'
          ),
      ],
      [
          InlineKeyboardButton(
              'Audio Only (MP3)', callback_data='bestaudio/best'
          )
      ],
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)
  await update.message.reply_text(
      'Choose your preferred quality:', reply_markup=reply_markup
  )


async def button_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
  query = update.callback_query
  await query.answer()

  user_id = query.from_user.id
  selected_format = query.data
  url = user_links.get(user_id)

  if not url:
    await query.edit_message_text(
        'Session expired. Please send the link again.'
    )
    return

  await query.edit_message_text(
      'Downloading video in requested format... Please wait.'
  )

  output_filename = f'video_{user_id}.mp4'

  ydl_opts = {
      'format': selected_format,
      'outtmpl': output_filename,
      'merge_output_format': 'mp4',
  }

  try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
      ydl.download([url])

    await query.message.reply_text('Uploading to Telegram...')
    with open(output_filename, 'rb') as video_file:
      await context.bot.send_document(
          chat_id=query.message.chat_id, document=video_file
      )

    if os.path.exists(output_filename):
      os.remove(output_filename)

  except Exception as e:
    await query.message.reply_text(f'An error occurred: {str(e)}')


if __name__ == '__main__':
  # Start the Flask web server in a separate background thread
  threading.Thread(target=run_flask, daemon=True).start()

  # Run the Telegram Bot
  app = (
      ApplicationBuilder()
      .token('8950091020:AAHVvatmxRbCfZ47rzD-Qui6pnKKu7QMCYY')
      .build()
  )

  app.add_handler(CommandHandler('start', start))
  app.add_handler(
      MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
  )
  app.add_handler(CallbackQueryHandler(button_callback))

  print('Bot running...')
  app.run_polling()
