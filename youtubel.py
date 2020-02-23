from __future__ import unicode_literals
import youtube_dl
from telegram.ext import Updater, CommandHandler, callbackcontext, MessageHandler, Filters, messagequeue, CallbackQueryHandler
from telegram import ChatAction, Update, User, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.utils.request import Request
import telegram.bot
import re
import os
import logging
from functools import wraps
from pymongo import MongoClient
from pymongo.collection import Collection

# import urllib.request
# import cv2

client = MongoClient(os.environ.get("MONGODB_URI"))
db = client.get_default_database()
users: Collection = db.users
downloaded_audios: Collection = db.downloaded_audios


class MyLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)


def my_hook(msg):
    if msg['status'] == 'finished':
        print(msg)


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

youtube_regex = (
    r'(https?://)?(www\.)?'
    '(youtube|youtu|youtube-nocookie)\.(com|be)/'
    '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')

youtube_playlist_regex = '(https?://)?(www\.)?(?:youtube\.com.*(?:\?|&)(?:list)=)((?!videoseries)[a-zA-Z0-9_]*)'


ydl_video_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'max_filesize': 50_000_000,
    'outtmpl': "assets/audio/%(id)s.%(ext)s",
    'progress_hooks': [my_hook],
    'logger': MyLogger()
}


class MQBot(telegram.bot.Bot):
    '''A subclass of Bot which delegates send method handling to MQ'''
    def __init__(self, *args, is_queued_def=True, mqueue=None, **kwargs):
        super(MQBot, self).__init__(*args, **kwargs)
        # below 2 attributes should be provided for decorator usage
        self._is_messages_queued_default = is_queued_def
        self._msg_queue = mqueue or messagequeue.MessageQueue()

    def __del__(self):
        try:
            self._msg_queue.stop()
        except:
            pass

    @messagequeue.queuedmessage
    def send_message(self, *args, **kwargs):

        return super(MQBot, self).send_message(*args, **kwargs)


def handler(func):
    @wraps(func)
    def wrapped(update, context: callbackcontext, *args, **kwargs):
        _user: User = update.effective_user
        if (user := users.find_one({'_id': _user.id})) is None:
            user = {
                '_id': _user.id,
                'first_name': _user.first_name,
                'last_name': _user.last_name,
                'username': _user.username,
                'downloads': []
            }
            users.insert_one(user)
        chat = update.effective_chat
        message = update.message
        return func(update, context, user=user, chat=chat, message=message, _user=_user, *args, **kwargs)
    return wrapped


@handler
def start(update, context: callbackcontext, user, chat, message, _user):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Hi! I download and send audios from Youtube videos in MP3.\n\n" +
                                  "Send me a 🔗link to Youtube video and i will send you audio from it.\n\n" +
                                  # "[🌟 Star me on GitHub!](https://github.com/Lyubomur2201/youtubel) | " +
                                  # "[⚠️ Report an issue](https://github.com/Lyubomur2201/youtubel/issues)\n" +
                                  "👨🏻‍💻 Developed by *@lyubomyr_2201*", parse_mode=telegram.ParseMode.MARKDOWN)


def downloaded_audio_from_video(update, context, user, chat, message, _user: User, video_url):
    print(user)
    try:
        video_id = re.match(
            '^.*(?:(?:youtu\.be\/|v\/|vi\/|u\/\w\/|embed\/)|(?:(?:watch)?\?v(?:i)?=|\&v(?:i)?=))([^#\&\?]*).*',
            video_url)[1]
        video_url = f'http://youtu.be/{video_id}'

        if (video := downloaded_audios.find_one({'_id': video_id})) is None:
            with youtube_dl.YoutubeDL(ydl_video_opts) as ydl:
                info = ydl.extract_info(video_url, False)
                raw_title = info['title']
                video_id = info['id']
                ydl.download([video_url])
                performer, title = info['uploader'], raw_title
                if len((temp := raw_title.split("-"))) == 2:
                    performer = temp[0]
                    title = temp[1]

                audio = open(f"assets/audio/{video_id}.mp3", 'rb')
                context.bot.send_chat_action(chat_id=chat.id, action=ChatAction.UPLOAD_DOCUMENT)
                sent_doc = _user.send_audio(audio, duration=info['duration'], performer=performer,
                                            title=title, caption="@youtubel_bot")
                audio_id = sent_doc['audio']['file_id']
                downloaded_audios.insert_one({
                    '_id': info['id'],
                    'uploader': info['uploader'],
                    'uploader_id': info['uploader_id'],
                    'channel_id': info['channel_id'],
                    'upload_date': info['upload_date'],
                    'license': info['license'],
                    'creator': info['creator'],
                    'title': info['title'],
                    'thumbnail': info['thumbnail'],
                    'tags': info['tags'],
                    'audio_id': audio_id,
                })
        else:
            audio_id = video['audio_id']
            context.bot.send_chat_action(chat_id=chat.id, action=ChatAction.UPLOAD_DOCUMENT)
            _user.send_document(document=audio_id, caption="@youtubel_bot")

        if video_id not in user['downloads']:
            users.update_one({'_id': user['_id']}, {'$push': {'downloads': video_id}})

        context.bot.delete_message(chat_id=chat.id, message_id=message.message_id)
    except FileNotFoundError and OSError:
        context.bot.send_message(chat_id=chat.id, text="We could`nt get audio from this video, maybe its too big",
                                 reply_to_message_id=message.message_id)
        context.bot.send_sticker(chat_id=chat.id,
                                 sticker=open('assets/stickers/ThisIsFine.tgs', 'rb'))
    finally:
        try:
            os.remove(f"assets/audio/{video_id}.mp3")
        except UnboundLocalError:
            pass
        except FileNotFoundError:
            pass


@handler
def youtube_link(update, context: callbackcontext, user, chat, message, _user, *args, **kwargs):
    video_url = message.text
    downloaded_audio_from_video(update=update, context=context, user=user, chat=chat,
                                message=message, _user=_user, video_url=video_url)

# def prepare_thumbnail(thumbnail_url):
#     print(thumbnail_url)
#     thumbnail_path = f"{thumbnail_url.split('/')[-2]}.jpeg"
#     urllib.request.urlretrieve(thumbnail_url, thumbnail_path)
#     # image = cv2.imread(thumbnail_path, cv2.IMREAD_UNCHANGED)
#     # print(image.shape)
#     # width = int(320)
#     # height = int(320)
#     # dim = (width, height)
#     # resized = cv2.resize(image, dim, interpolation=cv2.INTER_AREA)
#     # cv2.imwrite(thumbnail_path, resized)
#     return thumbnail_path
#
#
# ydl_playlist_opts = {
#     'format': 'bestaudio/best',
#     'postprocessors': [{
#         'key': 'FFmpegExtractAudio',
#         'preferredcodec': 'mp3',
#         'preferredquality': '192',
#     }],
#     'dump_single_json': True,
#     'extract_flat': True,
#     'ignoreerrors': True,
#     'outtmpl': "assets/audio/%(id)s.%(ext)s",
#     'progress_hooks': [my_hook],
#     'logger': MyLogger()
# }
#
#
# @handler
# def youtube_playlist(update, context, user, chat, message, _user: User):
#     playlist_url = message.text
#     info = youtube_dl.YoutubeDL(ydl_playlist_opts).extract_info(playlist_url, False)
#     for entry in info['entries']:
#         if entry['_type'] == 'url':
#             keyboard = [[InlineKeyboardButton('Download', callback_data=f"DOWNLOAD:{entry['id']}")],
#                         [InlineKeyboardButton('Delete', callback_data='DELETE')]]
#             markup = InlineKeyboardMarkup(keyboard)
#             _user.send_message(text=entry['title'], reply_markup=markup)


@handler
def unknown(update, context, user, chat, message, _user):
    _user.send_message(text="Unknown message")


# @handler
# def video_markup_callback(update: Update, context, user, chat, message, _user):
#     query: telegram.CallbackQuery = update.callback_query
#     if query.data == 'DELETE':
#         context.bot.delete_message(chat_id=chat.id, message_id=query.message.message_id)
#     elif query.data.startswith("DOWNLOAD:"):
#         video_id = query.data[9:]
#         video_url = f'http://youtu.be/{video_id}'
#         downloaded_audio_from_video(update=update, context=context, user=user, video_url=video_url,
#                                     chat=chat, message=query.message, _user=_user)


if __name__ == '__main__':
    try:

        q = messagequeue.MessageQueue(all_burst_limit=20, all_time_limit_ms=1100)
        request = Request(con_pool_size=8)
        bot = MQBot(os.environ.get("BOT_TOKEN"), request=request, mqueue=q)
        updater = Updater(bot=bot, use_context=True)
        dispatcher = updater.dispatcher

        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(MessageHandler(Filters.regex(re.compile(youtube_regex)), youtube_link))
        # dispatcher.add_handler(MessageHandler(Filters.regex(re.compile(youtube_playlist_regex)), youtube_playlist))
        # updater.dispatcher.add_handler(CallbackQueryHandler(video_markup_callback))
        dispatcher.add_handler(MessageHandler(Filters.all, unknown))
        updater.start_polling()
    except telegram.error.TimedOut:
        print("TIMEOUT!!!")
