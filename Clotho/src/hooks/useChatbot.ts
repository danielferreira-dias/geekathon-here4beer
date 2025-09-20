import { useState, useCallback } from "react";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export function useChatbot() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "1",
      role: "assistant",
      content:
        "Hello! I'm your AI Forecasting and Planning Copilot for the meat factory. I can help you analyze sales data, create production plans, and provide supply chain insights. How can I assist you today?",
      timestamp: new Date(),
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);

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

      // Create a placeholder assistant message for streaming
      const assistantMessageId = (Date.now() + 1).toString();
      const assistantMessage: ChatMessage = {
        id: assistantMessageId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);

      try {
        // Get API URL from environment
        const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

        // Prepare the conversation history for the API
        const conversationHistory = [...messages, userMessage].map((msg) => ({
          role: msg.role,
          content: msg.content,
        }));

        const response = await fetch(`${apiUrl}/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            messages: conversationHistory,
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

        // Stream the response
        while (true) {
          const { done, value } = await reader.read();

          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split("\n");

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.slice(6));

                if (data.content) {
                  // Update the assistant message with streaming content
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === assistantMessageId
                        ? { ...msg, content: msg.content + data.content }
                        : msg
                    )
                  );
                }

                if (data.done) {
                  break;
                }
              } catch (error) {
                console.error("Error parsing JSON:", error);
                // Skip invalid JSON lines
                continue;
              }
            }
          }
        }
      } catch (error) {
        console.error("Error sending message:", error);

        // Replace the assistant message with an error message
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
      } finally {
        setIsLoading(false);
      }
    },
    [messages, isLoading]
  );

  const clearChat = useCallback(() => {
    setMessages([
      {
        id: "1",
        role: "assistant",
        content:
          "Hello! I'm your AI Forecasting and Planning Copilot for the meat factory. I can help you analyze sales data, create production plans, and provide supply chain insights. How can I assist you today?",
        timestamp: new Date(),
      },
    ]);
  }, []);

  return {
    messages,
    isLoading,
    sendMessage,
    clearChat,
  };
}
