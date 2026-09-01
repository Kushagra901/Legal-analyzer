"use client";

import React, { useState, useEffect, useRef } from "react";
import { apiClient, ChatHistoryItem, ChatCitationResponse, SourceChunk } from "@/lib/api/client";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

interface DocumentChatDrawerProps {
  documentId: string;
  onSelectSnippet?: (snippetText: string) => void;
  activeSnippet?: string | null;
}

export function DocumentChatDrawer({
  documentId,
  onSelectSnippet,
  activeSnippet
}: DocumentChatDrawerProps) {
  const [messages, setMessages] = useState<ChatHistoryItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [sending, setSending] = useState<boolean>(false);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const SUGGESTED_PROMPTS = [
    "Who are the parties to this agreement?",
    "What is the notice period for termination?",
    "What is the liability cap?",
    "What law governs this agreement?"
  ];

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setLoading(true);
        const history = await apiClient.getDocumentChatHistory(documentId);
        setMessages(history);
      } catch (err) {
        console.error("Failed to load chat history:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, [documentId]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, sending]);

  const handleSend = async (query: string) => {
    if (!query.trim() || sending) return;

    const userMessage: ChatHistoryItem = {
      id: Date.now().toString(),
      role: "user",
      content: query,
      citations: [],
      created_at: new Date().toISOString()
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setSending(true);

    try {
      const response = await apiClient.sendDocumentChat(documentId, query);
      const assistantMessage: ChatHistoryItem = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.answer,
        citations: response.citations || [],
        confidence: response.confidence,
        created_at: new Date().toISOString()
      };
      setMessages((prev) => [...prev, assistantMessage]);

      // If response includes source chunks and user provided snippet callback, highlight first relevant snippet
      if (response.citations && response.citations.length > 0 && onSelectSnippet) {
        const firstSnippet = response.citations[0].snippet;
        if (firstSnippet) {
          onSelectSnippet(firstSnippet);
        }
      }
    } catch (err) {
      console.error("Failed to send message:", err);
    } finally {
      setSending(false);
    }
  };

  const handleSnippetClick = (text: string) => {
    if (onSelectSnippet && text) {
      onSelectSnippet(text);
    }
  };

  return (
    <Card className="h-full flex flex-col rounded-none border-[var(--border-subtle)] bg-[var(--bg-surface)]">
      <CardHeader className="py-3 px-4 flex flex-col space-y-2 border-b border-[var(--border-subtle)]">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-serif font-bold text-[var(--accent-primary)]">
            Document Q&amp;A Assistant
          </CardTitle>
          <span className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider font-mono">
            Grounded Citations
          </span>
        </div>
        <div className="flex flex-wrap gap-1.5 pt-1">
          {SUGGESTED_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => handleSend(prompt)}
              disabled={sending || loading}
              className="text-[10px] font-sans px-2 py-1 bg-[var(--bg-page)] text-[var(--text-main)] border border-[var(--border-subtle)] hover:border-[var(--accent-primary)] hover:bg-[var(--bg-surface)] transition-colors disabled:opacity-50 text-left"
            >
              {prompt}
            </button>
          ))}
        </div>
      </CardHeader>

      <CardContent
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-4 flex flex-col bg-[var(--bg-page)]"
      >
        {loading ? (
          <div className="space-y-4">
            <Skeleton className="h-14 w-3/4 rounded-none" />
            <Skeleton className="h-14 w-3/4 rounded-none ml-auto" />
            <Skeleton className="h-20 w-4/5 rounded-none" />
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-[var(--text-muted)] text-xs text-center p-6 space-y-2">
            <p className="font-semibold text-[var(--text-main)]">No conversation yet</p>
            <p className="max-w-xs">Ask any question about terms, parties, obligations, or termination notice periods to start.</p>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex flex-col max-w-[90%] ${msg.role === "user" ? "ml-auto items-end" : "mr-auto items-start"}`}
            >
              <div
                className={`p-3 rounded-none text-xs leading-relaxed ${
                  msg.role === "user"
                    ? "bg-[var(--accent-primary)] text-white"
                    : "bg-[var(--bg-surface)] border border-[var(--border-subtle)] border-l-2 border-l-[var(--accent-primary)] text-[var(--text-main)]"
                }`}
              >
                <div className="whitespace-pre-wrap">{msg.content}</div>

                {msg.role === "assistant" && msg.citations && msg.citations.length > 0 && (
                  <div className="mt-3 border-t border-[var(--border-subtle)] pt-2.5 space-y-1.5">
                    <span className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider font-semibold block">
                      Cited Document Excerpts (Click to View in Text):
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {msg.citations.map((cite, idx) => {
                        const snippetText = cite.snippet || cite.clause_type || "";
                        const isMatch = Boolean(
                          activeSnippet &&
                          snippetText &&
                          (activeSnippet.toLowerCase().includes(snippetText.toLowerCase().slice(0, 30)) ||
                           snippetText.toLowerCase().includes(activeSnippet.toLowerCase().slice(0, 30)))
                        );
                        return (
                          <button
                            key={idx}
                            type="button"
                            onClick={() => handleSnippetClick(snippetText)}
                            title={cite.snippet || "Click to jump to document source"}
                            className={`text-[10px] px-2 py-0.5 font-mono border transition-colors cursor-pointer text-left ${
                              isMatch
                                ? "bg-[#fef3c7] text-[#92400e] border-[#d97706] font-bold"
                                : "bg-[var(--bg-page)] text-[var(--accent-primary)] border-[var(--border-subtle)] hover:bg-[var(--border-subtle)]"
                            }`}
                          >
                            📍 {cite.clause_type}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                {msg.role === "assistant" && (
                  <div className="mt-2 pt-2 border-t border-[var(--border-subtle)] text-[10px] text-[var(--text-muted)] italic">
                    AI response assists legal review; never replaces licensed counsel.
                  </div>
                )}
              </div>
            </div>
          ))
        )}

        {sending && (
          <div className="mr-auto items-start max-w-[90%]">
            <div className="p-3 rounded-none bg-[var(--bg-surface)] border border-[var(--border-subtle)] border-l-2 border-l-[var(--accent-primary)] space-y-2">
              <Skeleton className="h-3 w-44 rounded-none" />
              <Skeleton className="h-3 w-32 rounded-none" />
            </div>
          </div>
        )}
      </CardContent>

      <CardFooter className="border-t border-[var(--border-subtle)] p-3 bg-[var(--bg-surface)]">
        <form
          className="flex w-full space-x-2"
          onSubmit={(e) => {
            e.preventDefault();
            handleSend(input);
          }}
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about this contract..."
            disabled={sending || loading}
            className="flex-1 text-xs border-[var(--border-subtle)] bg-[var(--bg-page)] text-[var(--text-main)] rounded-none"
          />
          <Button
            type="submit"
            variant="primary"
            disabled={sending || loading || !input.trim()}
            className="shrink-0 text-xs px-3 py-1.5"
          >
            {sending ? "Searching..." : "Send"}
          </Button>
        </form>
      </CardFooter>
    </Card>
  );
}
