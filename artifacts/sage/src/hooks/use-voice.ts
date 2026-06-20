import { useState, useRef, useCallback, useEffect } from "react";

interface UseVoiceOptions {
  onTranscript?: (text: string) => void;
  onError?: (err: string) => void;
}

export interface VoiceState {
  isListening: boolean;
  isSpeaking: boolean;
  voiceEnabled: boolean;
  supported: boolean;
  interim: string;
}

export function useVoice({ onTranscript, onError }: UseVoiceOptions = {}) {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [interim, setInterim] = useState("");
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const synthRef = useRef(window.speechSynthesis);

  const supported =
    typeof window !== "undefined" &&
    ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
    setIsListening(false);
    setInterim("");
  }, []);

  const startListening = useCallback(() => {
    if (!supported) {
      onError?.("Speech recognition not supported in this browser.");
      return;
    }
    synthRef.current.cancel();

    const SRCtor =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const recognition: SpeechRecognition = new SRCtor();
    recognition.lang = "en-US";
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognition.continuous = false;

    recognition.onstart = () => setIsListening(true);

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interimText = "";
      let finalText = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalText += t;
        } else {
          interimText += t;
        }
      }
      setInterim(interimText);
      if (finalText) {
        setInterim("");
        onTranscript?.(finalText.trim());
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      if (event.error !== "aborted") onError?.(event.error);
      setIsListening(false);
      setInterim("");
    };

    recognition.onend = () => {
      setIsListening(false);
      setInterim("");
    };

    recognitionRef.current = recognition;
    recognition.start();
  }, [supported, onTranscript, onError]);

  const toggleListening = useCallback(() => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  }, [isListening, startListening, stopListening]);

  const speak = useCallback(
    (text: string) => {
      if (!voiceEnabled || !text) return;
      synthRef.current.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.05;
      utterance.pitch = 0.95;
      utterance.volume = 1;

      const voices = synthRef.current.getVoices();
      const preferred = voices.find(
        (v) =>
          v.name.toLowerCase().includes("google") &&
          v.lang.startsWith("en")
      ) || voices.find((v) => v.lang.startsWith("en"));
      if (preferred) utterance.voice = preferred;

      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);

      synthRef.current.speak(utterance);
    },
    [voiceEnabled]
  );

  const stopSpeaking = useCallback(() => {
    synthRef.current.cancel();
    setIsSpeaking(false);
  }, []);

  const toggleVoice = useCallback(() => {
    setVoiceEnabled((v) => {
      if (v) {
        synthRef.current.cancel();
        recognitionRef.current?.stop();
        setIsListening(false);
        setIsSpeaking(false);
      }
      return !v;
    });
  }, []);

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();
      synthRef.current.cancel();
    };
  }, []);

  return {
    isListening,
    isSpeaking,
    voiceEnabled,
    supported,
    interim,
    toggleListening,
    toggleVoice,
    speak,
    stopSpeaking,
  };
}
