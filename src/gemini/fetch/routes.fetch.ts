import type { Request, Response } from "express";
import { aegisFetchHandler } from "./aegisFetch.express";
export async function fetchExpressHandler(req: Request, res: Response) {
  return aegisFetchHandler(req, res);
}
