import type { Request, Response } from "express";
import { geminiAskGuarded } from "../index";

export async function askExpressHandler(req: Request, res: Response) {
  const { status, body } = await geminiAskGuarded({
    prompt: req.body?.prompt ?? "",
    system: req.body?.system,
    options: req.body?.options,
    clientKey: req.ip || req.headers["x-forwarded-for"]?.toString()
  });
  return res.status(status).json(body);
}
