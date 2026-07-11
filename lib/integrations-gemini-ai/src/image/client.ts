import { GoogleGenAI, Modality } from "@google/genai";

const apiKey = process.env.GEMINI_API_KEY || process.env.AI_INTEGRATIONS_GEMINI_API_KEY;

const baseUrl = process.env.AI_INTEGRATIONS_GEMINI_BASE_URL;

// Make Gemini optional — don't crash if no API key is set.
const ai: GoogleGenAI | null = apiKey
  ? new GoogleGenAI({
      apiKey,
      ...(baseUrl
        ? {
            httpOptions: {
              apiVersion: "",
              baseUrl,
            },
          }
        : {}),
    })
  : null;

export async function generateImage(
  prompt: string
): Promise<{ b64_json: string; mimeType: string }> {
  if (!ai) {
    throw new Error(
      "Image generation requires GEMINI_API_KEY to be set. Groq does not support image generation."
    );
  }

  const response = await ai.models.generateContent({
    model: "gemini-2.5-flash-image",
    contents: [{ role: "user", parts: [{ text: prompt }] }],
    config: {
      responseModalities: [Modality.TEXT, Modality.IMAGE],
    },
  });

  const candidate = response.candidates?.[0];
  const imagePart = candidate?.content?.parts?.find(
    (part: { inlineData?: { data?: string; mimeType?: string } }) => part.inlineData
  );

  if (!imagePart?.inlineData?.data) {
    throw new Error("No image data in response");
  }

  return {
    b64_json: imagePart.inlineData.data,
    mimeType: imagePart.inlineData.mimeType || "image/png",
  };
}
