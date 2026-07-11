import { GoogleGenAI } from "@google/genai";

const apiKey = process.env.GEMINI_API_KEY || process.env.AI_INTEGRATIONS_GEMINI_API_KEY;

// Make Gemini optional — don't crash if no API key is set.
// Callers should check `ai !== null` before using it.
export const ai: GoogleGenAI | null = apiKey
  ? new GoogleGenAI({
      apiKey,
      ...(process.env.AI_INTEGRATIONS_GEMINI_BASE_URL
        ? {
            httpOptions: {
              apiVersion: "",
              baseUrl: process.env.AI_INTEGRATIONS_GEMINI_BASE_URL,
            },
          }
        : {}),
    })
  : null;
