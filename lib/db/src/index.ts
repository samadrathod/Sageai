import { drizzle } from "drizzle-orm/libsql";
import { createClient } from "@libsql/client";
import path from "path";
import * as schema from "./schema";

const currentDir = import.meta.dirname || (typeof __dirname !== "undefined" ? __dirname : "");
const dbPath = process.env.DATABASE_URL || `file:${path.resolve(currentDir, "..", "..", "..", "lib", "db", "sqlite.db")}`;
const sqlite = createClient({ url: dbPath });
export const db = drizzle(sqlite, { schema });

export * from "./schema";
