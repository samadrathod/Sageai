import { sqliteTable, text, integer } from "drizzle-orm/sqlite-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";

export const todosTable = sqliteTable("todos", {
  id: integer("id", { mode: "number" }).primaryKey({ autoIncrement: true }),
  title: text("title").notNull(),
  completed: integer("completed", { mode: "boolean" }).notNull().default(false),
  priority: text("priority").notNull().default("medium"),
  createdAt: integer("created_at", { mode: "timestamp" }).notNull().$defaultFn(() => new Date()),
});

export const insertTodoSchema = createInsertSchema(todosTable).omit({ id: true, createdAt: true });
export type InsertTodo = z.infer<typeof insertTodoSchema>;
export type Todo = typeof todosTable.$inferSelect;
