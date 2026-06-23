import { Router, type IRouter } from "express";
import { eq, desc } from "drizzle-orm";
import os from "os";
import { db, conversations, messages, memoriesTable } from "@workspace/db";
import {
  SendGeminiMessageParams,
  SendGeminiMessageBody,
  GetGeminiConversationParams,
  DeleteGeminiConversationParams,
  ListGeminiMessagesParams,
  CreateGeminiConversationBody,
} from "@workspace/api-zod";
import { ai } from "@workspace/integrations-gemini-ai";
import { Type } from "@google/genai";
import { logger } from "../../lib/logger";

const router: IRouter = Router();

router.get("/gemini/conversations", async (req, res): Promise<void> => {
  const convos = await db
    .select()
    .from(conversations)
    .orderBy(desc(conversations.createdAt));
  res.json(convos);
});

router.post("/gemini/conversations", async (req, res): Promise<void> => {
  const parsed = CreateGeminiConversationBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }
  const [convo] = await db
    .insert(conversations)
    .values({ title: parsed.data.title })
    .returning();
  res.status(201).json(convo);
});

router.get("/gemini/conversations/:id", async (req, res): Promise<void> => {
  const params = GetGeminiConversationParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }
  const [convo] = await db
    .select()
    .from(conversations)
    .where(eq(conversations.id, params.data.id));
  if (!convo) {
    res.status(404).json({ error: "Conversation not found" });
    return;
  }
  const msgs = await db
    .select()
    .from(messages)
    .where(eq(messages.conversationId, params.data.id))
    .orderBy(messages.createdAt);
  res.json({ ...convo, messages: msgs });
});

router.delete("/gemini/conversations/:id", async (req, res): Promise<void> => {
  const params = DeleteGeminiConversationParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }
  const [convo] = await db
    .delete(conversations)
    .where(eq(conversations.id, params.data.id))
    .returning();
  if (!convo) {
    res.status(404).json({ error: "Conversation not found" });
    return;
  }
  res.sendStatus(204);
});

router.get("/gemini/conversations/:id/messages", async (req, res): Promise<void> => {
  const params = ListGeminiMessagesParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }
  const msgs = await db
    .select()
    .from(messages)
    .where(eq(messages.conversationId, params.data.id))
    .orderBy(messages.createdAt);
  res.json(msgs);
});

router.post("/gemini/conversations/:id/messages", async (req, res): Promise<void> => {
  const params = SendGeminiMessageParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }
  const parsed = SendGeminiMessageBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }

  const [convo] = await db
    .select()
    .from(conversations)
    .where(eq(conversations.id, params.data.id));
  if (!convo) {
    res.status(404).json({ error: "Conversation not found" });
    return;
  }

  const userMsg = parsed.data.content;

  // 1. Direct save option if local command was pre-executed on frontend/voice loop
  const localResponse = (req.body as any).localResponse;
  if (localResponse) {
    logger.info(`Persisting pre-executed local command response in DB for session ${params.data.id}`);
    await db.insert(messages).values({
      conversationId: params.data.id,
      role: "user",
      content: userMsg,
    });
    await db.insert(messages).values({
      conversationId: params.data.id,
      role: "assistant",
      content: localResponse,
    });
    res.json({ success: true });
    return;
  }

  // 2. Intercept local desktop command if it matches intent registry offline
  try {
    const agentRes = await fetch("http://localhost:7700/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: userMsg, confirmed: false }),
    });
    if (agentRes.ok) {
      const data = await agentRes.json() as any;
      if (data.handled) {
        logger.info(`Local command intercepted at backend: intent=${data.intent}`);
        
        // If it requires confirmation, stream the request
        if (data.requires_confirm) {
          res.setHeader("Content-Type", "text/event-stream");
          res.setHeader("Cache-Control", "no-cache");
          res.setHeader("Connection", "keep-alive");
          res.write(`data: ${JSON.stringify({ requires_confirm: true, confirm_description: data.confirm_description })}\n\n`);
          res.end();
          return;
        }

        // Save user message and local execution response
        await db.insert(messages).values({
          conversationId: params.data.id,
          role: "user",
          content: userMsg,
        });
        await db.insert(messages).values({
          conversationId: params.data.id,
          role: "assistant",
          content: data.response,
        });

        // Stream output to dashboard/voice client
        res.setHeader("Content-Type", "text/event-stream");
        res.setHeader("Cache-Control", "no-cache");
        res.setHeader("Connection", "keep-alive");
        res.write(`data: ${JSON.stringify({ content: data.response })}\n\n`);
        res.write(`data: ${JSON.stringify({ done: true })}\n\n`);
        res.end();
        return;
      }
    }
  } catch (err) {
    logger.error("Failed to route local command check to agent: " + err);
  }

  // Save user message to database
  await db.insert(messages).values({
    conversationId: params.data.id,
    role: "user",
    content: userMsg,
  });

  // Load history for context
  const history = await db
    .select()
    .from(messages)
    .where(eq(messages.conversationId, params.data.id))
    .orderBy(messages.createdAt);

  // Load user memories to inject into system prompt
  const memoriesList = await db.select().from(memoriesTable);
  const memoryContext = memoriesList.length > 0
    ? `\n\nHere is what you know about the user (memories/preferences):\n${memoriesList.map(m => `- [ID: ${m.id}, Category: ${m.category}] ${m.content}`).join("\n")}`
    : "\n\nYou have no current memories of the user.";

  const SAGE_SYSTEM = `You are SAGE (Smart Adaptive Guidance Engine), a highly intelligent, precise, and personable AI assistant. You are knowledgeable, concise, and always helpful. You remember context within the conversation. You are capable of helping with tasks, answering questions, writing, coding, and analysis. You are not a generic chatbot — you are SAGE, built to be a true personal assistant.${memoryContext}`;

  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");

  let fullResponse = "";

  // 3. System condition check for model routing (Ollama)
  let isLowResource = false;
  try {
    const freeMem = os.freemem();
    const totalMem = os.totalmem();
    const percentUsed = ((totalMem - freeMem) / totalMem) * 100;
    
    const agentSysRes = await fetch("http://localhost:7700/system/info");
    if (agentSysRes.ok) {
      const sysData = await agentSysRes.json() as any;
      const memPercent = sysData.memory?.percent ?? percentUsed;
      const batteryPercent = sysData.battery?.percent ?? 100;
      const powerPlugged = sysData.battery?.power_plugged ?? true;
      if (memPercent > 80 || (batteryPercent < 25 && !powerPlugged)) {
        isLowResource = true;
      }
    } else if (percentUsed > 80) {
      isLowResource = true;
    }
  } catch (err) {
    const freeMem = os.freemem();
    const totalMem = os.totalmem();
    const percentUsed = ((totalMem - freeMem) / totalMem) * 100;
    if (percentUsed > 80) {
      isLowResource = true;
    }
  }

  // Pick local Ollama model
  let ollamaModel = "qwen3:4b";
  const isCodingPrompt = /\b(code|python|javascript|ts|js|html|css|react|node|rust|c\+\+|java|c#|golang|compiler|git|github|debug|refactor|error|exception|syntax|api|function|class|method|develop|programming)\b/i.test(userMsg);
  
  if (isLowResource) {
    ollamaModel = "phi3:mini";
  } else if (isCodingPrompt) {
    ollamaModel = "qwen2.5-coder:3b";
  }

  // 4. Try Ollama execution first (Local-First)
  let ollamaSuccess = false;
  try {
    logger.info(`Targeting Ollama model: ${ollamaModel} for prompt. LowResource=${isLowResource}, Coding=${isCodingPrompt}`);
    
    const messagesToSend = [
      { role: "system", content: SAGE_SYSTEM },
      ...history.slice(0, -1).map(m => ({
        role: m.role === "assistant" ? "assistant" : "user",
        content: m.content
      })),
      { role: "user", content: userMsg }
    ];

    const response = await fetch("http://localhost:11434/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: ollamaModel,
        messages: messagesToSend,
        stream: true,
        options: {
          keep_alive: "5m"
        }
      })
    });

    if (response.ok && response.body) {
      ollamaSuccess = true;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.trim()) {
            const data = JSON.parse(line);
            const content = data.message?.content || "";
            if (content) {
              fullResponse += content;
              res.write(`data: ${JSON.stringify({ content })}\n\n`);
            }
          }
        }
      }
    } else {
      logger.warn(`Ollama responded with status: ${response.status}. Falling back to cloud.`);
    }
  } catch (error: any) {
    logger.warn(`Ollama connection failed: ${error.message}. Falling back to cloud.`);
  }

  // 5. Cloud Fallback if Ollama was not successful
  if (!ollamaSuccess) {
    let cloudSuccess = false;
    
    // Fallback 1: Groq API
    const groqKey = process.env.GROQ_API_KEY;
    if (groqKey) {
      try {
        logger.info("Using Groq Cloud API fallback...");
        const groqMessages = [
          { role: "system", content: SAGE_SYSTEM },
          ...history.slice(0, -1).map(m => ({
            role: m.role === "assistant" ? "assistant" : "user",
            content: m.content
          })),
          { role: "user", content: userMsg }
        ];

        const response = await fetch("https://api.groq.com/openai/v1/chat/completions", {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${groqKey}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            model: "llama3-8b-8192",
            messages: groqMessages,
            stream: true
          })
        });

        if (response.ok && response.body) {
          cloudSuccess = true;
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
              const cleanedLine = line.trim();
              if (cleanedLine.startsWith("data: ")) {
                const dataStr = cleanedLine.slice(6).trim();
                if (dataStr === "[DONE]") break;
                try {
                  const data = JSON.parse(dataStr);
                  const content = data.choices?.[0]?.delta?.content || "";
                  if (content) {
                    fullResponse += content;
                    res.write(`data: ${JSON.stringify({ content })}\n\n`);
                  }
                } catch {
                  // ignore JSON parse error
                }
              }
            }
          }
        }
      } catch (err: any) {
        logger.error(`Groq fallback failed: ${err.message}`);
      }
    }

    // Fallback 2: Gemini API (Secondary Cloud)
    if (!cloudSuccess) {
      try {
        logger.info("Using Gemini Cloud API secondary fallback...");
        const chatMessages: any[] = [
          { role: "user" as const, parts: [{ text: SAGE_SYSTEM }] },
          { role: "model" as const, parts: [{ text: "Understood. I am SAGE, ready to assist you." }] },
          ...history.map((m) => ({
            role: m.role === "assistant" ? ("model" as const) : ("user" as const),
            parts: [{ text: m.content }],
          })),
        ];

        let currentMessages = [...chatMessages];
        let finalStream;
        let retries = 0;

        while (retries < 3) {
          const response = await ai.models.generateContent({
            model: "gemini-2.5-flash",
            contents: currentMessages,
            config: {
              maxOutputTokens: 8192,
              tools: [
                {
                  functionDeclarations: [
                    {
                      name: "save_preference_or_fact",
                      description: "Save a user preference, hobby, or personal fact to SAGE memory. Use this whenever the user explicitly tells you something about themselves, their settings preferences, or personal details.",
                      parameters: {
                        type: Type.OBJECT,
                        properties: {
                          content: { type: Type.STRING, description: "The memory content (e.g. 'User prefers VS Code for Python')" },
                          category: { type: Type.STRING, description: "The category, e.g. 'preference', 'hobby', 'personal', 'work'." }
                        },
                        required: ["content"]
                      }
                    },
                    {
                      name: "delete_preference_or_fact",
                      description: "Delete an outdated or incorrect preference or fact from memory using its database ID. Use list_memories or look at the system prompt list to find the ID.",
                      parameters: {
                        type: Type.OBJECT,
                        properties: {
                          id: { type: Type.INTEGER, description: "The integer ID of the memory to delete." }
                        },
                        required: ["id"]
                      }
                    },
                    {
                      name: "execute_desktop_command",
                      description: "Execute a local desktop command (e.g. open an application like VS Code, Chrome, Spotify, Calculator, File Explorer, Task Manager; search files; rename/delete files; stop/kill processes; show system info). Use this whenever the user wants to perform an action on their computer.",
                      parameters: {
                        type: Type.OBJECT,
                        properties: {
                          command: { type: Type.STRING, description: "The natural language desktop command to execute (e.g. 'open chrome', 'search for resume', 'kill spotify', 'show cpu status')" }
                        },
                        required: ["command"]
                      }
                    }
                  ]
                }
              ]
            }
          });

          const functionCalls = response.functionCalls;
          if (!functionCalls || functionCalls.length === 0) {
            finalStream = await ai.models.generateContentStream({
              model: "gemini-2.5-flash",
              contents: currentMessages,
              config: { maxOutputTokens: 8192 }
            });
            break;
          }

          const functionResponses: any[] = [];
          for (const call of functionCalls) {
            logger.info(`Gemini called function: ${call.name} with args: ${JSON.stringify(call.args)}`);
            let responseContent = {};

            if (call.name === "save_preference_or_fact") {
              const args = call.args as { content: string; category?: string };
              const [mem] = await db.insert(memoriesTable).values({
                content: args.content,
                category: args.category || "general"
              }).returning();
              responseContent = { success: true, memory: mem };
            } else if (call.name === "delete_preference_or_fact") {
              const args = call.args as { id: number };
              const [mem] = await db.delete(memoriesTable).where(eq(memoriesTable.id, args.id)).returning();
              responseContent = { success: !!mem };
            } else if (call.name === "execute_desktop_command") {
              const args = call.args as { command: string };
              try {
                const agentRes = await fetch("http://localhost:7700/execute", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ message: args.command, confirmed: true }),
                });
                if (agentRes.ok) {
                  const data = await agentRes.json() as { handled: boolean; response: string };
                  responseContent = { success: data.handled, response: data.response };
                } else {
                  responseContent = { success: false, error: `Agent responded with status: ${agentRes.status}` };
                }
              } catch (err: any) {
                responseContent = { success: false, error: err.message };
              }
            }

            functionResponses.push({
              name: call.name,
              response: responseContent,
              id: call.id
            });
          }

          currentMessages.push({
            role: "model" as const,
            parts: functionCalls.map(c => ({ functionCall: c }))
          });
          currentMessages.push({
            role: "user" as const,
            parts: functionResponses.map(r => ({ functionResponse: r }))
          });

          retries++;
        }

        if (!finalStream) {
          finalStream = await ai.models.generateContentStream({
            model: "gemini-2.5-flash",
            contents: currentMessages,
            config: { maxOutputTokens: 8192 }
          });
        }

        for await (const chunk of finalStream) {
          const text = chunk.text;
          if (text) {
            fullResponse += text;
            res.write(`data: ${JSON.stringify({ content: text })}\n\n`);
          }
        }
      } catch (err: any) {
        logger.error(`Gemini fallback failed: ${err.message}`);
        res.write(`data: ${JSON.stringify({ content: `\n⚠ Error generating response: ${err.message}` })}\n\n`);
      }
    }
  }

  // Save the assistant's final response to database
  if (fullResponse) {
    await db.insert(messages).values({
      conversationId: params.data.id,
      role: "assistant",
      content: fullResponse,
    });
  }

  res.write(`data: ${JSON.stringify({ done: true })}\n\n`);
  res.end();
});

export default router;
