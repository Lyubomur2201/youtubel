from __future__ import unicode_literals
import youtube_dl
from telegram.ext import Updater, CommandHandler, callbackcontext, MessageHandler, Filters
from telegram import ChatAction
import re
import os

import logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

youtube_regex = (
    r'(https?://)?(www\.)?'
    '(youtube|youtu|youtube-nocookie)\.(com|be)/'
    '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')

print(os.environ.get("BOT_TOKEN"))
updater = Updater(token=os.environ.get("BOT_TOKEN"), use_context=True)
dispatcher = updater.dispatcher


def start(update, context: callbackcontext):
    # print(update.message.from_user)
    # print(context.bot)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=f"I'm a bot, please {update.message.from_user.username} talk to me!")


def youtube_link(update, context: callbackcontext):
    video_url = update.message.text

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': 'assets/audio/%(title)s.%(ext)s',
        # 'progress_hooks': [my_hook],
        # 'logger': MyLogger()
    }
    try:

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            raw_title = ydl.extract_info(video_url, False)['title']
            ydl.download([video_url])
            performer, title = None, None
            if len((temp := raw_title.split("-"))) == 2:
                performer = temp[0]
                title = temp[1]

        context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)
        context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(f'assets/audio/{raw_title}.mp3', 'rb'),
                               performer=performer if performer is not None else None,
                               title=title if title is not None else raw_title)

        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
    except youtube_dl.utils.DownloadError as e:
        if "This playlist is private" in str(e):
            context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, this playlist is private")
            context.bot.send_sticker(chat_id=update.effective_chat.id,
                                     sticker=open('assets/stickers/ThisIsFine.tgs', 'rb'))

    finally:
        try:
            os.remove(f'uploads/audio/{raw_title}.mp3')
        except UnboundLocalError:
            pass


def unknown(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="unknown message")


dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.regex(re.compile(youtube_regex)), youtube_link))
dispatcher.add_handler(MessageHandler(Filters.all, unknown))
updater.start_polling()

#
# class MyLogger(object):
#     def debug(self, msg):
#         pass
#
#     def warning(self, msg):
#         pass
#
#     def error(self, msg):
#         print(msg)
#
#
# def my_hook(d):
#     print(d)
#
#
