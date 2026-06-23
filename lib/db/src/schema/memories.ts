import { sqliteTable, text, integer } from "drizzle-orm/sqlite-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";

export const memoriesTable = sqliteTable("memories", {
  id: integer("id", { mode: "number" }).primaryKey({ autoIncrement: true }),
  content: text("content").notNull(),
  category: text("category").notNull().default("general"),
  createdAt: integer("created_at", { mode: "timestamp" }).notNull().$defaultFn(() => new Date()),
});

export const insertMemorySchema = createInsertSchema(memoriesTable).omit({ id: true, createdAt: true });
export type InsertMemory = z.infer<typeof insertMemorySchema>;
export type Memory = typeof memoriesTable.$inferSelect;
