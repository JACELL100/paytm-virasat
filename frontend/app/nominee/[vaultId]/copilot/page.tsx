"use client";

import { use, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Mic, Square, Send, ListChecks, FileDown } from "lucide-react";
import { SimpleShell } from "@/components/layout/simple-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCard?: { type: "claim_plan"; items: Array<{ label: string; reason: string }> };
}

const GREETING =
  "Namaste. I'm Sahayak — I'll help your family find and claim everything, one step at a time. What would you like to know first?";

export default function CopilotPage({ params }: { params: Promise<{ vaultId: string }> }) {
  const { vaultId } = use(params);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { id: "greeting", role: "assistant", content: GREETING },
  ]);
  const [input, setInput] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api
      .post<{ id: string }>(`/copilot/${vaultId}/sessions`)
      .then((res) => setSessionId(res.id))
      .catch(() => setSessionId(`demo-${vaultId}`));
  }, [vaultId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function sendMessage(text: string) {
    if (!text.trim()) return;
    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsThinking(true);

    try {
      await api.post(`/copilot/sessions/${sessionId}/messages`, { content: text });
      // Backend streams over SSE in production; fall through to the demo reply below
      // until the SSE client is wired up.
      throw new Error("use-demo-fallback");
    } catch {
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content:
              "First, let's stop the loan EMIs — the Bajaj Finance business loan has protection cover, so that claim is most urgent. Next, the HDFC Life term policy. I've ranked everything for you below.",
            toolCard: {
              type: "claim_plan",
              items: [
                { label: "Bajaj Finance — loan protection", reason: "Stops EMIs immediately" },
                { label: "HDFC Life — term policy ₹50L", reason: "Largest payout, documents ready" },
                { label: "LIC — endowment ₹10L", reason: "Straightforward, nominee confirmed" },
              ],
            },
          },
        ]);
        setIsThinking(false);
      }, 900);
    } finally {
      setIsThinking(false);
    }
  }

  async function toggleRecording() {
    if (isRecording) {
      mediaRecorderRef.current?.stop();
      setIsRecording(false);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];
      recorder.ondataavailable = (e) => chunksRef.current.push(e.data);
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const fd = new FormData();
        fd.append("audio", blob, "voice.webm");
        setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", content: "🎙 Voice message" }]);
        setIsThinking(true);
        try {
          await api.upload(`/copilot/sessions/${sessionId}/voice`, fd);
        } catch {
          // demo fallback
        }
        setTimeout(() => {
          setMessages((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              role: "assistant",
              content: "I heard you. Let's start with the most urgent claim — the loan protection cover.",
            },
          ]);
          setIsThinking(false);
        }, 1200);
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "assistant", content: "I couldn't access your microphone. You can type instead." },
      ]);
    }
  }

  return (
    <SimpleShell homeHref={`/nominee/${vaultId}`}>
      <div className="flex h-[calc(100vh-7rem)] flex-col">
        <div className="mb-3">
          <h1 className="font-display text-xl font-bold text-text">Sahayak</h1>
          <p className="text-xs text-muted">Your claim co-pilot, in Hindi, Marathi or English</p>
        </div>

        <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto rounded-2xl border border-border bg-surface p-4">
          {messages.map((m) => (
            <motion.div
              key={m.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}
            >
              <div
                className={cn(
                  "max-w-[80%] rounded-2xl px-4 py-2.5 text-sm",
                  m.role === "user"
                    ? "brand-gradient text-white"
                    : "bg-surface-2 text-text",
                )}
              >
                <p>{m.content}</p>
                {m.toolCard && (
                  <div className="mt-3 space-y-2 rounded-xl border border-border bg-surface p-3">
                    <p className="flex items-center gap-1.5 text-xs font-semibold text-brand-navy dark:text-brand-cyan">
                      <ListChecks className="size-3.5" /> Ranked claim plan
                    </p>
                    {m.toolCard.items.map((item, i) => (
                      <div key={i} className="flex items-start justify-between gap-2 text-xs">
                        <span className="font-medium text-text">
                          {i + 1}. {item.label}
                        </span>
                        <Badge variant="outline" className="shrink-0">
                          {item.reason}
                        </Badge>
                      </div>
                    ))}
                    <Button size="sm" variant="outline" className="w-full">
                      <FileDown className="size-3.5" /> Generate claim pack
                    </Button>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
          <AnimatePresence>
            {isThinking && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex justify-start">
                <div className="flex items-center gap-1 rounded-2xl bg-surface-2 px-4 py-3">
                  {[0, 1, 2].map((i) => (
                    <motion.span
                      key={i}
                      className="size-1.5 rounded-full bg-muted"
                      animate={{ opacity: [0.3, 1, 0.3] }}
                      transition={{ duration: 1, repeat: Infinity, delay: i * 0.15 }}
                    />
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="mt-3 flex items-center gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage(input)}
            placeholder="Type your question, or use the mic…"
            className="flex-1"
          />
          <Button variant="outline" size="icon" onClick={() => sendMessage(input)} aria-label="Send">
            <Send className="size-4" />
          </Button>
          <Button
            size="icon"
            variant={isRecording ? "destructive" : "brand"}
            onClick={toggleRecording}
            aria-label={isRecording ? "Stop recording" : "Record voice message"}
            className="relative"
          >
            {isRecording && (
              <motion.span
                className="absolute inset-0 rounded-lg bg-danger/40"
                animate={{ scale: [1, 1.4], opacity: [0.6, 0] }}
                transition={{ duration: 1.2, repeat: Infinity }}
              />
            )}
            {isRecording ? <Square className="size-4" /> : <Mic className="size-4" />}
          </Button>
        </div>
      </div>
    </SimpleShell>
  );
}
