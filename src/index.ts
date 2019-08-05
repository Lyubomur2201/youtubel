import fs from "fs";
import Telegraf from "telegraf";
import { config } from "dotenv";
//@ts-ignore
import commandParts from "telegraf-command-parts";
import { replyWithAudio } from "./utils";

const youtubeRegEx = /^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$/g;

config();

const telegraf = new Telegraf(process.env.BOT_TOKEN || "");

telegraf.use(commandParts());
telegraf.start(async ctx => {
  ctx.reply("Hello new user.");
});

telegraf.command(
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

telegraf.command(
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

telegraf.hears(
  youtubeRegEx,
  (ctx, next) => {
    //@ts-ignore
    ctx.state.url = ctx.message!.text;
    next!();
  },
  replyWithAudio
);

telegraf.use(ctx => {
  ctx.reply("Sorry this massage is not supported.");
});

fs.exists("assets/audio", exists => {
  if (exists) {
    telegraf.launch();
  } else {
    fs.mkdir("assets/audio", error => {
      if (error === null) {
        telegraf.launch();
      }
    });
  }
});
