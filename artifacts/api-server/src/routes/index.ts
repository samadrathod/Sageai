import { Router, type IRouter } from "express";
import healthRouter from "./health";
import geminiRouter from "./gemini";
import notesRouter from "./notes";
import todosRouter from "./todos";
import statsRouter from "./stats";
import memoriesRouter from "./memories";

const router: IRouter = Router();

router.use(healthRouter);
router.use(geminiRouter);
router.use(notesRouter);
router.use(todosRouter);
router.use(statsRouter);
router.use(memoriesRouter);

export default router;
