"use client";

import React, { useState, useEffect, useRef } from "react";
import { apiClient, ChatHistoryItem, ChatCitationResponse } from "@/lib/api/client";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

interface DocumentChatDrawerProps {
  documentId: string;
}

export function DocumentChatDrawer({ documentId }: DocumentChatDrawerProps) {
  const [messages, setMessages] = useState<ChatHistoryItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [sending, setSending] = useState<boolean>(false);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const SUGGESTED_PROMPTS = [
    "What is my liability cap?",
    "Can I terminate early?",
    "What are the payment terms?",
    "Are there non-compete clauses?"
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
    } catch (err) {
      console.error("Failed to send message:", err);
    } finally {
      setSending(false);
    }
  };

  return (
    <Card className="h-full flex flex-col rounded-sm border-[#e0dfdb] bg-[#faf9f6]">
      <CardHeader className="border-b border-[#e0dfdb] py-4">
        <CardTitle className="text-base text-[#0d1b2a]">Document Assistant</CardTitle>
        <div className="flex flex-wrap gap-2 mt-2">
          {SUGGESTED_PROMPTS.map((prompt) => (
            <Button
              key={prompt}
              variant="outline"
              onClick={() => handleSend(prompt)}
              disabled={sending || loading}
              className="rounded-none border-[#e0dfdb] text-[#0d1b2a] text-xs h-8 py-1 px-2.5"
            >
              {prompt}
            </Button>
          ))}
        </div>
      </CardHeader>
      
      <CardContent 
        ref={scrollRef} 
        className="flex-1 overflow-y-auto p-6 space-y-6 flex flex-col bg-[#faf9f6]"
      >
        {loading ? (
          <div className="space-y-4">
            <Skeleton className="h-16 w-3/4 rounded-sm" />
            <Skeleton className="h-16 w-3/4 rounded-sm ml-auto" />
            <Skeleton className="h-24 w-4/5 rounded-sm" />
          </div>
        ) : messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-[#8a8985] text-sm">
            Ask a question about this document to get started.
          </div>
        ) : (
          messages.map((msg) => (
            <div 
              key={msg.id} 
              className={`flex flex-col max-w-[85%] ${msg.role === "user" ? "ml-auto items-end" : "mr-auto items-start"}`}
            >
              <div 
                className={`p-4 rounded-sm text-sm ${
                  msg.role === "user" 
                    ? "bg-[#0d1b2a] text-[#faf9f6]" 
                    : "bg-white border border-[#e0dfdb] border-l-2 border-l-[#0d1b2a] text-[#0d1b2a]"
                }`}
              >
                <div className="whitespace-pre-wrap">{msg.content}</div>
                
                {msg.role === "assistant" && msg.citations && msg.citations.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5 border-t border-[#e0dfdb] pt-3">
                    <span className="text-xs text-[#8a8985] mr-1 block w-full">Citations:</span>
                    {msg.citations.map((cite, idx) => (
                      <Badge 
                        key={idx} 
                        variant="neutral" 
                        className="rounded-none border-[#e0dfdb] text-xs cursor-pointer hover:bg-gray-50"
                        title={cite.snippet}
                      >
                        {cite.clause_type}
                      </Badge>
                    ))}
                  </div>
                )}
                
                {msg.role === "assistant" && (
                  <div className="mt-3 pt-3 border-t border-[#e0dfdb] text-[10px] text-[#8a8985] italic">
                    AI-generated content. Consult legal counsel for final review.
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        
        {sending && (
          <div className="mr-auto items-start max-w-[85%]">
            <div className="p-4 rounded-sm bg-white border border-[#e0dfdb] border-l-2 border-l-[#0d1b2a]">
              <Skeleton className="h-4 w-48 rounded-sm mb-2" />
              <Skeleton className="h-4 w-32 rounded-sm" />
            </div>
          </div>
        )}
      </CardContent>
      
      <CardFooter className="border-t border-[#e0dfdb] p-4 bg-[#faf9f6]">
        <form 
          className="flex w-full space-x-2" 
          onSubmit={(e) => { e.preventDefault(); handleSend(input); }}
        >
          <Input 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about this contract..." 
            disabled={sending || loading}
            className="flex-1 rounded-sm border-[#e0dfdb] bg-white text-[#0d1b2a]"
          />
          <Button 
            type="submit" 
            disabled={sending || loading || !input.trim()}
            className="rounded-sm bg-[#0d1b2a] text-[#faf9f6] hover:bg-[#1a2838]"
          >
            Send
          </Button>
        </form>
      </CardFooter>
    </Card>
  );
}
