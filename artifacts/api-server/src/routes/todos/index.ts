import { Router, type IRouter } from "express";
import { eq, desc } from "drizzle-orm";
import { db, todosTable } from "@workspace/db";
import {
  CreateTodoBody,
  UpdateTodoBody,
  UpdateTodoParams,
  DeleteTodoParams,
} from "@workspace/api-zod";

const router: IRouter = Router();

router.get("/todos", async (_req, res): Promise<void> => {
  const todos = await db
    .select()
    .from(todosTable)
    .orderBy(desc(todosTable.createdAt));
  res.json(todos);
});

router.post("/todos", async (req, res): Promise<void> => {
  const parsed = CreateTodoBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }
  const [todo] = await db.insert(todosTable).values(parsed.data).returning();
  res.status(201).json(todo);
});

router.patch("/todos/:id", async (req, res): Promise<void> => {
  const params = UpdateTodoParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }
  const parsed = UpdateTodoBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }
  const [todo] = await db
    .update(todosTable)
    .set(parsed.data)
    .where(eq(todosTable.id, params.data.id))
    .returning();
  if (!todo) {
    res.status(404).json({ error: "Todo not found" });
    return;
  }
  res.json(todo);
});

router.delete("/todos/:id", async (req, res): Promise<void> => {
  const params = DeleteTodoParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }
  const [todo] = await db
    .delete(todosTable)
    .where(eq(todosTable.id, params.data.id))
    .returning();
  if (!todo) {
    res.status(404).json({ error: "Todo not found" });
    return;
  }
  res.sendStatus(204);
});

export default router;
