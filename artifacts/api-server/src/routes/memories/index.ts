import { Router, type IRouter } from "express";
import { eq, desc } from "drizzle-orm";
import { db, memoriesTable } from "@workspace/db";
import { CreateMemoryBody, DeleteMemoryParams } from "@workspace/api-zod";

const router: IRouter = Router();

router.get("/memories", async (_req, res): Promise<void> => {
  try {
    const memories = await db
      .select()
      .from(memoriesTable)
      .orderBy(desc(memoriesTable.createdAt));
    res.json(memories);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

router.post("/memories", async (req, res): Promise<void> => {
  const parsed = CreateMemoryBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }
  try {
    const [memory] = await db
      .insert(memoriesTable)
      .values({
        content: parsed.data.content,
        category: parsed.data.category || "general",
      })
      .returning();
    res.status(201).json(memory);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

router.delete("/memories/:id", async (req, res): Promise<void> => {
  const params = DeleteMemoryParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }
  try {
    const [memory] = await db
      .delete(memoriesTable)
      .where(eq(memoriesTable.id, params.data.id))
      .returning();
    if (!memory) {
      res.status(404).json({ error: "Memory not found" });
      return;
    }
    res.sendStatus(204);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

export default router;
