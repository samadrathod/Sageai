import { Router, type IRouter } from "express";
import { db, conversations, messages, notesTable, todosTable } from "@workspace/db";
import { eq, count } from "drizzle-orm";

const router: IRouter = Router();

router.get("/stats", async (_req, res): Promise<void> => {
  const [[convCount], [msgCount], [noteCount], [todoCount], [completedCount]] =
    await Promise.all([
      db.select({ count: count() }).from(conversations),
      db.select({ count: count() }).from(messages),
      db.select({ count: count() }).from(notesTable),
      db.select({ count: count() }).from(todosTable),
      db
        .select({ count: count() })
        .from(todosTable)
        .where(eq(todosTable.completed, true)),
    ]);
  res.json({
    totalConversations: convCount?.count ?? 0,
    totalMessages: msgCount?.count ?? 0,
    totalNotes: noteCount?.count ?? 0,
    totalTodos: todoCount?.count ?? 0,
    completedTodos: completedCount?.count ?? 0,
  });
});

export default router;
