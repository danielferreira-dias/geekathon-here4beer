import { useState, useCallback } from "react";
import { useAnalysisContext } from "@/contexts/AnalysisContext";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export function useChatbot() {
  const { conversationId, resetConversationId } = useAnalysisContext();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "1",
      role: "assistant",
      content: "Hello! How can I assist you today?",
      timestamp: new Date(),
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isLoading) return;

      const userMessage: ChatMessage = {
        id: Date.now().toString(),
        role: "user",
        content: content.trim(),
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);

      // We'll create the assistant message only when we start receiving content
      let assistantMessageId: string | null = null;

      try {
        // Get API URL from environment
        const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

        const response = await fetch(`${apiUrl}/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            question: content.trim(),
            conversation_id: conversationId,
          }),
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        // Check if the response supports streaming
        if (!response.body) {
          throw new Error("Response body is not available for streaming");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        // Stream the response (plain text streaming)
        while (true) {
          const { done, value } = await reader.read();

          if (done) break;

          const chunk = decoder.decode(value, { stream: true });

          // Handle plain text streaming - each chunk is part of the response
          if (chunk && chunk.trim()) {
            // Only process non-empty chunks
            // Create assistant message on first content if it doesn't exist
            if (!assistantMessageId) {
              assistantMessageId = (Date.now() + 1).toString();
              const assistantMessage: ChatMessage = {
                id: assistantMessageId,
                role: "assistant",
                content: chunk,
                timestamp: new Date(),
              };
              setMessages((prev) => [...prev, assistantMessage]);
              setIsStreaming(true); // Mark as streaming started
              setIsLoading(false); // Hide loading indicator once we have actual text content
            } else {
              // Update existing assistant message with streaming content
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMessageId
                    ? { ...msg, content: msg.content + chunk }
                    : msg
                )
              );
            }
          }
        }
      } catch (error) {
        console.error("Error sending message:", error);

        // Create or replace the assistant message with an error message
        if (!assistantMessageId) {
          // No assistant message was created yet, create one with error
          const errorMessageId = (Date.now() + 1).toString();
          const errorMessage: ChatMessage = {
            id: errorMessageId,
            role: "assistant",
            content:
              "I apologize, but I encountered an error processing your request. Please try again or contact support if the issue persists.",
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, errorMessage]);
        } else {
          // Replace existing assistant message with error
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? {
                    ...msg,
                    content:
                      "I apologize, but I encountered an error processing your request. Please try again or contact support if the issue persists.",
                  }
                : msg
            )
          );
        }
      } finally {
        setIsLoading(false);
        setIsStreaming(false);
      }
    },
    [isLoading, conversationId]
  );

  const clearChat = useCallback(() => {
    setMessages([
      {
        id: "1",
        role: "assistant",
        content: "Hello! How can I assist you today?",
        timestamp: new Date(),
      },
    ]);
    resetConversationId();
  }, [resetConversationId]);

  return {
    messages,
    isLoading,
    isStreaming,
    sendMessage,
    clearChat,
  };
}
