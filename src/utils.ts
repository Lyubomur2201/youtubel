import fs from "fs";
import youtubedl from "youtube-dl";
import { ContextMessageUpdate } from "telegraf";

interface AudioInfo {
  videoId?: string;
  duration?: number;
  performer?: string;
  name?: string;
}
// TODO: Unlink file on error
export const replyWithAudio = async (ctx: ContextMessageUpdate) => {
  //@ts-ignore
  const { url } = ctx.state;

  const filePath = "assets/audio/" + url.split("/").pop() + ".mp3";

  let video = youtubedl(url, ["--extract-audio", "--audio-format", "mp3"], {
    cwd: __dirname
  });

  let audioInfo: AudioInfo = {};

  video.on("info", function(info) {
    let name = info._filename;
    let nameArray = name.split("-").map(item => item.replace("_", " "));

    nameArray.pop();

    if (nameArray.length === 2) {
      audioInfo = {
        name: nameArray[1].trim(),
        performer: nameArray[0].trim()
      };
    } else {
      name = nameArray.join("-");
      audioInfo = {
        name
      };
    }
    audioInfo.duration = Number(info._duration_raw);

    console.log("Download started");
    console.log("filename: " + info._filename);
    console.log("size: " + info.size);
  });

  //@ts-ignore
  video.on("error", (info: Error) => {
    if (info.message.includes("This playlist is private")) {
      ctx.reply("This playlist is private.");
      ctx.replyWithSticker({ source: "assets/stickers/ThisIsFine.tgs" });
      fs.unlink(filePath, error => {
        if (error != null) throw error;
      });
    } else {
      console.log(info.message);

      ctx.reply("Sorry we can't get audio from that video.");
      ctx.replyWithSticker({ source: "assets/stickers/ThisIsNotFine.tgs" });
    }
  });

  let audioStream = fs.createWriteStream(filePath);

  video.pipe(audioStream);

  audioStream.on("close", async () => {
    try {
      await ctx.replyWithAudio(
        {
          source: filePath
        },
        {
          title: audioInfo!.name,
          performer: audioInfo.performer,
          duration: audioInfo.duration
        }
      );
    } catch (error) {
      if (error.message.includes("Request Entity Too Large")) {
        ctx.reply("This video is to long.");
      }
    } finally {
      fs.unlink(filePath, error => {
        if (error != null) throw error;
      });
    }
  });
};
