import { useState, useRef, useEffect, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import {
  MessageSquare,
  Send,
  Plus,
  Trash2,
  Terminal,
  Loader2,
  Zap,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  MonitorPlay,
} from "lucide-react";
import {
  useListGeminiConversations,
  useCreateGeminiConversation,
  useGetGeminiConversation,
  useDeleteGeminiConversation,
  getListGeminiConversationsQueryKey,
  getGetGeminiConversationQueryKey,
} from "@workspace/api-client-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { useVoice } from "@/hooks/use-voice";
import { useDesktopAgent } from "@/hooks/use-desktop-agent";

export default function ChatPage() {
  const queryClient = useQueryClient();
  const [activeId, setActiveId] = useState<number | null>(null);
  const [inputMessage, setInputMessage] = useState("");
  const [streamingText, setStreamingText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const pendingDesktopRef = useRef<string | null>(null);

  const { connected: agentConnected, executeIntent, confirmPending, dismissPending, pendingConfirm } = useDesktopAgent();

  const handleTranscript = useCallback((text: string) => {
    setInputMessage(text);
    setTimeout(() => {
      inputRef.current?.form?.requestSubmit();
    }, 100);
  }, []);

  const { isListening, isSpeaking, voiceEnabled, supported: voiceSupported, interim, toggleListening, toggleVoice, speak, stopSpeaking } = useVoice({
    onTranscript: handleTranscript,
  });

  const { data: conversations, isLoading: isLoadingConvos } = useListGeminiConversations();
  const createConvo = useCreateGeminiConversation();
  console.log("VALUE:", conversations);
console.log("TYPE:", typeof conversations);
console.log("IS ARRAY:", Array.isArray(conversations));
console.log("JSON:", JSON.stringify(conversations));
  const deleteConvo = useDeleteGeminiConversation();

  const { data: activeConvo, isLoading: isLoadingActive } = useGetGeminiConversation(
    activeId!,
    { query: { enabled: !!activeId, queryKey: getGetGeminiConversationQueryKey(activeId!) } }
  );

  useEffect(() => {
  if (
    Array.isArray(conversations) &&
    conversations.length > 0 &&
    !activeId
  ) {
    setActiveId(conversations[0].id);
  }
}, [conversations, activeId]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [activeConvo?.messages, streamingText]);

  const handleCreateConvo = () => {
    createConvo.mutate(
      { data: { title: "New Conversation" } },
      {
        onSuccess: (newConvo) => {
          queryClient.invalidateQueries({ queryKey: getListGeminiConversationsQueryKey() });
          setActiveId(newConvo.id);
          setTimeout(() => inputRef.current?.focus(), 100);
        },
      }
    );
  };

  const handleDeleteConvo = (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    deleteConvo.mutate(
      { id },
      {
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: getListGeminiConversationsQueryKey() });
          if (activeId === id) setActiveId(null);
        },
      }
    );
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || !activeId || isStreaming) return;

    const userMsg = inputMessage;
    setInputMessage("");
    setIsStreaming(true);
    setStreamingText("");

    // Try desktop agent intent first
    if (agentConnected) {
      const intentResult = await executeIntent(userMsg);
      if (intentResult?.handled) {
        // Add user message + agent response to chat optimistically
        queryClient.setQueryData(getGetGeminiConversationQueryKey(activeId), (old: any) => {
          if (!old) return old;
          return {
            ...old,
            messages: [
              ...old.messages,
              { id: Date.now(), conversationId: activeId, role: "user", content: userMsg, createdAt: new Date().toISOString() },
              { id: Date.now() + 1, conversationId: activeId, role: "assistant", content: intentResult.response, createdAt: new Date().toISOString() },
            ],
          };
        });
        if (voiceEnabled) speak(intentResult.response);
        
        // Persist local execution to backend DB
        try {
          await fetch(`/api/gemini/conversations/${activeId}/messages`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ content: userMsg, localResponse: intentResult.response }),
          });
        } catch (e) {
          console.error("Failed to persist local command: ", e);
        }

        setIsStreaming(false);
        queryClient.invalidateQueries({ queryKey: getGetGeminiConversationQueryKey(activeId) });
        return;
      }
    }

    // Optimistically add user message
    queryClient.setQueryData(getGetGeminiConversationQueryKey(activeId), (old: any) => {
      if (!old) return old;
      return {
        ...old,
        messages: [
          ...old.messages,
          { id: Date.now(), conversationId: activeId, role: "user", content: userMsg, createdAt: new Date().toISOString() },
        ],
      };
    });

    try {
      const response = await fetch(`/api/gemini/conversations/${activeId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: userMsg }),
      });

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let assistantText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const lines = decoder.decode(value).split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = JSON.parse(line.slice(6));
            if (data.done) break;
            if (data.content) {
              assistantText += data.content;
              setStreamingText(assistantText);
            }
          }
        }
      }

      if (voiceEnabled && assistantText) speak(assistantText);
    } catch (error) {
      console.error("Stream error:", error);
    } finally {
      setIsStreaming(false);
      setStreamingText("");
      queryClient.invalidateQueries({ queryKey: getGetGeminiConversationQueryKey(activeId) });
    }
  };

  return (
    <div className="flex h-full w-full relative z-10">
      {/* Conversations Sidebar */}
      <div className="w-72 flex flex-col border-r border-border/50 bg-card/30 backdrop-blur-md">
        <div className="p-4 border-b border-border/50">
          <Button
            onClick={handleCreateConvo}
            disabled={createConvo.isPending}
            className="w-full justify-start gap-2 bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20"
          >
            {createConvo.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            NEW_SESSION
          </Button>
        </div>

        <ScrollArea className="flex-1">
          <div className="p-2 space-y-1">
            {isLoadingConvos
              ? Array(5).fill(0).map((_, i) => <Skeleton key={i} className="h-12 w-full rounded-lg bg-border/20" />)
              : (Array.isArray(conversations) ? conversations : []).map((convo) => (
                  <div
                    key={convo.id}
                    onClick={() => setActiveId(convo.id)}
                    className={cn(
                      "group flex items-center justify-between p-3 rounded-lg cursor-pointer transition-all duration-200 border",
                      activeId === convo.id
                        ? "bg-primary/10 border-primary/30 text-primary shadow-[inset_0_0_15px_rgba(0,255,255,0.05)]"
                        : "bg-transparent border-transparent text-muted-foreground hover:bg-card/50 hover:text-foreground"
                    )}
                  >
                    <div className="flex items-center gap-3 overflow-hidden">
                      <MessageSquare className="w-4 h-4 shrink-0" />
                      <div className="truncate text-sm font-medium">{convo.title || "Untitled Session"}</div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="w-6 h-6 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive"
                      onClick={(e) => handleDeleteConvo(convo.id, e)}
                      disabled={deleteConvo.isPending}
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                ))}
          </div>
        </ScrollArea>

        {/* Desktop Agent Status */}
        <div className="p-3 border-t border-border/50">
          <div className={cn(
            "flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-mono border",
            agentConnected
              ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-400"
              : "border-border/30 bg-card/20 text-muted-foreground/50"
          )}>
            <MonitorPlay className="w-3 h-3 shrink-0" />
            <span>{agentConnected ? "DESKTOP_AGENT: ONLINE" : "DESKTOP_AGENT: OFFLINE"}</span>
            <div className={cn("ml-auto w-1.5 h-1.5 rounded-full", agentConnected ? "bg-emerald-400 animate-pulse" : "bg-muted-foreground/30")} />
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col relative bg-background/40">
        {activeId ? (
          <>
            <header className="h-14 flex items-center justify-between px-6 border-b border-border/50 bg-card/30 backdrop-blur-md shrink-0">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-primary" />
                <span className="font-mono text-sm tracking-wider opacity-80 text-primary">
                  SESSION_ID: {activeId.toString().padStart(6, "0")}
                </span>
              </div>
              <div className="flex items-center gap-2">
                {isSpeaking && (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={stopSpeaking}
                    className="h-8 w-8 text-primary/70 hover:text-primary animate-pulse"
                    title="Stop speaking"
                  >
                    <VolumeX className="w-4 h-4" />
                  </Button>
                )}
                {voiceSupported && (
                  <Tooltip delayDuration={0}>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={toggleVoice}
                        className={cn(
                          "h-8 w-8 transition-all duration-300 font-mono text-xs",
                          voiceEnabled
                            ? "text-primary border border-primary/30 bg-primary/5 shadow-[0_0_10px_rgba(0,255,255,0.1)]"
                            : "text-muted-foreground hover:text-foreground"
                        )}
                      >
                        {voiceEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" className="font-mono text-xs">
                      {voiceEnabled ? "VOICE: ON — click to mute" : "VOICE: OFF — click to enable TTS"}
                    </TooltipContent>
                  </Tooltip>
                )}
              </div>
            </header>

            {/* Confirmation Banner */}
            {pendingConfirm && (
              <div className="mx-4 mt-3 p-3 rounded-xl border border-amber-500/40 bg-amber-500/5 backdrop-blur-sm flex items-center gap-3">
                <div className="flex-1">
                  <p className="text-xs font-mono text-amber-400 tracking-wide">⚠ CONFIRM_ACTION</p>
                  <p className="text-sm text-foreground mt-0.5">{pendingConfirm.description}</p>
                </div>
                <div className="flex gap-2 shrink-0">
                  <Button size="sm" onClick={confirmPending} className="h-7 px-3 text-xs bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/30">
                    CONFIRM
                  </Button>
                  <Button size="sm" variant="ghost" onClick={dismissPending} className="h-7 px-3 text-xs text-muted-foreground hover:text-foreground">
                    CANCEL
                  </Button>
                </div>
              </div>
            )}

            <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6 scroll-smooth">
              {isLoadingActive ? (
                <div className="flex justify-center items-center h-full">
                  <Loader2 className="w-8 h-8 animate-spin text-primary/50" />
                </div>
              ) : activeConvo?.messages?.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center space-y-4 opacity-50">
                  <Zap className="w-16 h-16 text-primary mb-2" />
                  <h2 className="text-xl font-mono tracking-widest text-primary">SAGE.ONLINE</h2>
                  <p className="text-sm text-muted-foreground max-w-md">SYSTEM READY. AWAITING INPUT.</p>
                  {agentConnected && (
                    <p className="text-xs font-mono text-emerald-500/70 mt-2">DESKTOP AGENT ACTIVE — say "open VS Code" or "create folder called Projects"</p>
                  )}
                </div>
              ) : (
                <>
                  {activeConvo?.messages?.map((msg) => (
                    <div
                      key={msg.id}
                      className={cn("flex gap-4 max-w-3xl", msg.role === "user" ? "ml-auto flex-row-reverse" : "mr-auto")}
                    >
                      <div className={cn(
                        "w-8 h-8 shrink-0 rounded-lg flex items-center justify-center",
                        msg.role === "user"
                          ? "bg-secondary text-secondary-foreground"
                          : "bg-primary/20 text-primary border border-primary/30 shadow-[0_0_15px_rgba(0,255,255,0.1)]"
                      )}>
                        {msg.role === "user" ? "U" : <Zap className="w-4 h-4" />}
                      </div>
                      <div className={cn(
                        "px-4 py-3 rounded-2xl",
                        msg.role === "user"
                          ? "bg-secondary text-secondary-foreground"
                          : "bg-card/50 border border-border/50 text-foreground font-mono text-sm shadow-sm backdrop-blur-sm"
                      )}>
                        <div className="whitespace-pre-wrap">{msg.content}</div>
                      </div>
                    </div>
                  ))}
                  {isStreaming && (
                    <div className="flex gap-4 max-w-3xl mr-auto">
                      <div className="w-8 h-8 shrink-0 rounded-lg flex items-center justify-center bg-primary/20 text-primary border border-primary/30 shadow-[0_0_15px_rgba(0,255,255,0.1)]">
                        <Zap className="w-4 h-4" />
                      </div>
                      <div className="px-4 py-3 rounded-2xl bg-card/50 border border-border/50 text-foreground font-mono text-sm shadow-sm backdrop-blur-sm">
                        <div className="whitespace-pre-wrap">{streamingText}</div>
                        <span className="inline-block w-2 h-4 ml-1 bg-primary animate-pulse align-middle" />
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>

            <div className="p-4 bg-background/80 backdrop-blur-xl border-t border-border/50 shrink-0">
              <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto relative flex items-center gap-2">
                {/* Voice mic button */}
                {voiceSupported && (
                  <Tooltip delayDuration={0}>
                    <TooltipTrigger asChild>
                      <Button
                        type="button"
                        size="icon"
                        onClick={toggleListening}
                        disabled={isStreaming}
                        className={cn(
                          "h-14 w-14 shrink-0 rounded-xl transition-all duration-300 border",
                          isListening
                            ? "bg-red-500/20 border-red-500/50 text-red-400 shadow-[0_0_20px_rgba(255,50,50,0.2)] animate-pulse"
                            : voiceEnabled
                            ? "bg-primary/10 border-primary/30 text-primary hover:bg-primary/20"
                            : "bg-card border-border/50 text-muted-foreground hover:text-foreground hover:bg-card/80"
                        )}
                      >
                        {isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="top" className="font-mono text-xs">
                      {isListening ? "RECORDING — click to stop" : "Click to speak"}
                    </TooltipContent>
                  </Tooltip>
                )}

                <div className="relative flex-1">
                  <Input
                    ref={inputRef}
                    value={interim || inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    placeholder={isListening ? "Listening..." : "Transmit message to SAGE..."}
                    className={cn(
                      "pr-12 bg-card border-border/50 h-14 rounded-xl focus-visible:ring-primary/50 text-base shadow-sm font-mono placeholder:font-sans transition-all duration-300",
                      isListening && "border-red-500/40 shadow-[0_0_15px_rgba(255,50,50,0.1)] placeholder:text-red-400/60"
                    )}
                    disabled={isStreaming || isListening}
                  />
                  <Button
                    type="submit"
                    size="icon"
                    disabled={!inputMessage.trim() || isStreaming || isListening}
                    className="absolute right-2 top-1/2 -translate-y-1/2 h-10 w-10 bg-primary/10 hover:bg-primary/20 text-primary disabled:opacity-50 transition-colors"
                  >
                    <Send className="w-4 h-4" />
                  </Button>
                </div>
              </form>

              <div className="text-center mt-2 font-mono text-[10px] text-muted-foreground/50 tracking-widest">
                {isListening
                  ? "🔴 VOICE INPUT ACTIVE"
                  : isSpeaking
                  ? "🔊 SAGE SPEAKING..."
                  : "SAGE SECURE ENCLAVE V2.0"}
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center opacity-30 text-primary">
            <Zap className="w-24 h-24 mb-6" />
            <h2 className="text-2xl font-mono tracking-widest">SELECT_SESSION OR INITIATE_NEW</h2>
          </div>
        )}
      </div>
    </div>
  );
}
