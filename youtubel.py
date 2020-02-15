from __future__ import unicode_literals
import youtube_dl
from telegram.ext import Updater, CommandHandler, callbackcontext, MessageHandler, Filters
from telegram import ChatAction, Update, User
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

updater = Updater(token=os.environ.get("BOT_TOKEN"), use_context=True)
dispatcher = updater.dispatcher

ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'outtmpl': "assets/audio/%(id)s.%(ext)s",
    'progress_hooks': [my_hook],
    'logger': MyLogger()
}


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
        print(user)
        chat = update.effective_chat
        message = update.message
        return func(update, context, user=user, chat=chat, message=message, _user=_user, *args, **kwargs)
    return wrapped


@handler
def start(update, context: callbackcontext, user, chat, message, _user):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=f"I'm a bot, please {update.message.from_user.username} talk to me!")


@handler
def youtube_link(update, context: callbackcontext, user, chat, message, _user, *args, **kwargs):
    video_url = message.text
    try:

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, False)
            # thumbnail_path = prepare_thumbnail('/'.join(info['thumbnail'].split('/')[0: -1]) + '/maxresdefault.jpg')
            raw_title = info['title']
            video_id = info['id']
            ydl.download([video_url])
            print(info)
            performer, title = None, None
            if len((temp := raw_title.split("-"))) == 2:
                performer = temp[0]
                title = temp[1]

        context.bot.send_chat_action(chat_id=user['_id'], action=ChatAction.UPLOAD_DOCUMENT)
        _user.send_audio(audio=open(f"assets/audio/{video_id}.mp3", 'rb'),
                         performer=performer if performer is not None else None,
                         title=title if title is not None else raw_title)

        users.update_one({'_id': user['_id']}, {'$push': {'downloads': video_id}})

        if (video := downloaded_audios.find_one({'_id': info['id']})) is None:
            video = downloaded_audios.insert_one({
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
                'view_count': info['view_count'],
                'like_count': info['like_count'],
                'dislike_count': info['dislike_count']
            })
        else:
            downloaded_audios.update_one({"_id": video['_id']}, {'$set': {
                'license': info['license'],
                'creator': info['creator'],
                'title': info['title'],
                'thumbnail': info['thumbnail'],
                'tags': info['tags'],
                'view_count': info['view_count'],
                'like_count': info['like_count'],
                'dislike_count': info['dislike_count']
            }})

        context.bot.delete_message(chat_id=user['_id'], message_id=message.message_id)
    except youtube_dl.utils.DownloadError as e:
        if "This playlist is private" in str(e):
            context.bot.send_message(chat_id=chat.id, text="Sorry, this playlist is private")
            context.bot.send_sticker(chat_id=chat.id,
                                     sticker=open('assets/stickers/ThisIsFine.tgs', 'rb'))

    finally:
        try:
            os.remove(f"assets/audio/{video_id}.mp3")
        except UnboundLocalError:
            pass


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


@handler
def unknown(update, context, user, chat, message, _user):
    _user.send_message(text="Unknown message")
    # _user.send_sticker(sticker=open('assets/stickers/ThisIsFine.tgs', 'rb'))


dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.regex(re.compile(youtube_regex)), youtube_link))
dispatcher.add_handler(MessageHandler(Filters.all, unknown))
updater.start_polling()
