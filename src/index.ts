import fs from "fs";
import Telegraf from "telegraf";
import { config } from "dotenv";
//@ts-ignore
import commandParts from "telegraf-command-parts";
import { replyWithAudio } from "./utils";

import { createServer } from "http";
import express from "express";

const youtubeRegEx = /^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$/g;

config();

const bot = new Telegraf(process.env.BOT_TOKEN || "");

bot.use(commandParts());
bot.start(async ctx => {
  ctx.reply("Hello new user.");
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
  const server = createServer(express().use((req, res) => res.status(200)));
  server.listen(process.env.PORT, () => {
    bot.launch();
  });
};

fs.exists("assets/audio", exists => {
  if (exists) startBot();
  else {
    fs.mkdir("assets/audio", error => {
      if (error === null) startBot();
    });
  }
});
