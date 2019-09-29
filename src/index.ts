import fs from "fs";
import Telegraf from "telegraf";
import "dotenv/config";

//@ts-ignore
import commandParts from "telegraf-command-parts";
import { replyWithAudio } from "./utils";

import { createServer } from "http";
import express from "express";
import axios from "axios";

const youtubeRegEx = /^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$/g;

const bot = new Telegraf(process.env.BOT_TOKEN || "");

bot.use(commandParts());
// Files over 50 MB are split into parts due to Telegram Bot API limit.
bot.start(async ctx => {
  ctx.replyWithMarkdown(
    "Hi! I download and send audios from Youtube videos in MP3.\n" +
      "Send me a link to Youtube video and i will send you audio from it.\n" +
      "[🌟 Star me on GitHub!](https://github.com/Lyubomur2201/youtubel) | " +
      "[⚠️ Report an issue](https://github.com/Lyubomur2201/youtubel/issues)\n" +
      "👨🏻‍💻 Developed by *@lyubomyr_2201*"
  );
});

bot.command(
  "/link",
  (ctx, next) => {
    // @ts-ignore
    ctx.state.url = ctx.state.command.args;

    //@ts-ignore
    if (ctx.state.url.length === 0) {
      ctx.reply("No link provided.");
    } else {
      next!();
    }
  },
  replyWithAudio
);

bot.command(
  "/id",
  (ctx, next) => {
    //@ts-ignore
    if (ctx.state.command.args.length === 0) {
      ctx.reply("No id provided.");
    } else {
      //@ts-ignore
      ctx.state.url = "https://youtu.be/" + ctx.state.command.args;

      next!();
    }
  },
  replyWithAudio
);

bot.hears(
  youtubeRegEx,
  (ctx, next) => {
    //@ts-ignore
    ctx.state.url = ctx.message!.text;
    next!();
  },
  replyWithAudio
);

bot.use(ctx => {
  ctx.reply("Sorry this massage is not supported.");
});

const startBot = () => {
  const server = createServer(
    express().use((req, res) => res.status(200).end())
  );
  server.listen(process.env.PORT, () => {
    bot.launch();
  });
  setInterval(() => {
    try {
      axios.get("https://youtubel-bot.herokuapp.com/");
    } catch (e) {
      console.log(e);
    }
  }, 1000 * 60);
};

fs.exists("assets/audio", exists => {
  if (exists) startBot();
  else {
    fs.mkdir("assets/audio", error => {
      if (error === null) startBot();
    });
  }
});
