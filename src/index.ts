import fs from "fs";
import Telegraf from "telegraf";
import youtubedl from "youtube-dl";
import { config } from "dotenv";
import { generate } from "randomstring";
//@ts-ignore
import commandParts from "telegraf-command-parts";

interface AudioInfo {
  videoId?: string;
  duration?: number;
  performer?: string;
  name?: string;
}

config();

const telegraf = new Telegraf(process.env.BOT_TOKEN || "");

telegraf.use(commandParts());
telegraf.start(async ctx => {
  ctx.reply("Hello new user");
});

telegraf.command("/link", ctx => {
  // @ts-ignore
  const url = ctx.state.command.args;

  if (url.length === 0) {
    ctx.reply("No link provided");
  } else {
    let video = youtubedl(url, ["--audio-format", "mp3"], { cwd: __dirname });
    let audioInfo: AudioInfo = {
      videoId: generate(16)
    };

    video.on("info", function(info) {
      let name = info._filename;
      let nameArray = name.split("-");
      if (nameArray.length === 2) {
        audioInfo = {
          name: nameArray[1],
          performer: nameArray[0]
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
      } else {
        ctx.reply("Sorry we can't get audio from that video.");
        ctx.replyWithSticker({ source: "assets/stickers/ThisIsNotFine.tgs" });
      }
    });

    let audioStream = fs.createWriteStream(
      "assets/audio/" + (audioInfo.videoId || "default") + ".mp3"
    );

    video.pipe(audioStream);

    audioStream.on("close", async () => {
      await ctx.replyWithAudio(
        { source: "assets/audio/" + (audioInfo.videoId || "default") + ".mp3" },
        {
          title: audioInfo!.name,
          performer: audioInfo.performer,
          duration: audioInfo.duration
        }
      );
    });
  }
});

telegraf.launch();
