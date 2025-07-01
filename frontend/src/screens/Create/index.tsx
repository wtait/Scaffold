import styled from "styled-components";
import { Icon, Typography, Avatar } from "@beamcloud/design-system";
import {
  faHeart,
  faPlay,
  faSpinner,
  faRotateRight,
  faUpRightFromSquare,
  faMobile,
  faTablet,
  faDesktop,
} from "@fortawesome/pro-regular-svg-icons";
import { useState, useEffect, useRef, useCallback } from "react";
import { useMessageBus } from "../../hooks/useMessageBus";
import { BEAM_CONFIG } from "../../config/beam";
import { MessageType, Sender } from "../../types/messages";
import type { Message } from "../../types/messages";
import { useLocation } from "react-router-dom";

const DEVICE_SPECS = {
  mobile: { width: 390, height: 844 },
  tablet: { width: 768, height: 1024 },
  desktop: { width: "100%", height: "100%" },
};

const Create = () => {
  const [inputValue, setInputValue] = useState("");
  const [sidebarWidth, setSidebarWidth] = useState(400);
  const [isResizing, setIsResizing] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [iframeUrl, setIframeUrl] = useState("");
  const [iframeError, setIframeError] = useState(false);
  const [iframeReady, setIframeReady] = useState(false);
  const [isUpdateInProgress, setIsUpdateInProgress] = useState(false);
  const [initCompleted, setInitCompleted] = useState(false);
  const chatHistoryRef = useRef<HTMLDivElement>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const hasConnectedRef = useRef(false);
  const processedMessageIds = useRef<Set<string>>(new Set());
  const location = useLocation();
  const initialPromptSent = useRef(false);
  const [selectedDevice, setSelectedDevice] = useState<
    "mobile" | "tablet" | "desktop"
  >("desktop");

  const refreshIframe = useCallback(() => {
    if (iframeRef.current && iframeUrl && iframeUrl !== "/") {
      setIframeReady(false);
      setIframeError(false);

      // First refresh
      const currentSrc = iframeRef.current.src;
      iframeRef.current.src = "";

      setTimeout(() => {
        if (iframeRef.current) {
          iframeRef.current.src = currentSrc;

          // Second refresh after a longer delay
          setTimeout(() => {
            if (iframeRef.current) {
              iframeRef.current.src = "";

              setTimeout(() => {
                if (iframeRef.current) {
                  iframeRef.current.src = currentSrc;
                }
              }, 200);
            }
          }, 500);
        }
      }, 300);
    }
  }, [iframeUrl]);

  // Message handlers for different message types
  const messageHandlers = {
    [MessageType.INIT]: (message: Message) => {
      const id = message.id;
      if (id) {
        if (processedMessageIds.current.has(id)) {
          console.log("Skipping duplicate INIT message:", id);
          return;
        }
        processedMessageIds.current.add(id);
        console.log("Processing INIT message:", id);
      }

      if (message.data.url && message.data.sandbox_id) {
        setIframeUrl(message.data.url);
        setIframeError(false);
      }

      setMessages((prev) => {
        if (id) {
          const existingIndex = prev.findIndex((msg) => msg.id === id);
          if (existingIndex !== -1) {
            // Update in place
            return prev.map((msg, idx) =>
              idx === existingIndex
                ? {
                    ...msg,
                    timestamp: message.timestamp || msg.timestamp,
                    data: {
                      ...msg.data,
                      text: "Workspace loaded! You can now make edits here.",
                      sender: Sender.ASSISTANT,
                    },
                  }
                : msg
            );
          }
        }
        // Insert new
        return [
          ...prev,
          {
            ...message,
            timestamp: message.timestamp || Date.now(),
            data: {
              ...message.data,
              text: "Workspace loaded! You can now make edits here.",
              sender: Sender.ASSISTANT,
            },
          },
        ];
      });
      setInitCompleted(true);
    },

    [MessageType.ERROR]: (message: Message) => {
      setMessages((prev) => [
        ...prev,
        {
          ...message,
          timestamp: message.timestamp || Date.now(),
          data: {
            ...message.data,
            sender: Sender.ASSISTANT,
          },
        },
      ]);
    },

    [MessageType.AGENT_PARTIAL]: (message: Message) => {
      const text = message.data.text;
      const id = message.id;

      if (!id) {
        console.warn("AGENT_PARTIAL message missing id, ignoring:", message);
        return;
      }

      if (text && text.trim()) {
        setMessages((prev) => {
          const existingIndex = prev.findIndex((msg) => msg.id === id);
          if (existingIndex !== -1) {
            return prev.map((msg, idx) =>
              idx === existingIndex
                ? {
                    ...msg,
                    timestamp: message.timestamp || msg.timestamp,
                    data: {
                      ...msg.data,
                      text: text.replace(/\\/g, ""),
                      sender: Sender.ASSISTANT,
                      isStreaming: true,
                    },
                  }
                : msg
            );
          }
          // Insert new
          return [
            ...prev,
            {
              ...message,
              timestamp: message.timestamp || Date.now(),
              data: {
                ...message.data,
                text: text.replace(/\\/g, ""),
                isStreaming: true,
                sender: Sender.ASSISTANT,
              },
            },
          ];
        });
      }
    },

    [MessageType.AGENT_FINAL]: (message: Message) => {
      const text = message.data.text;
      const id = message.id;
      if (!id) {
        console.warn("AGENT_FINAL message missing id, ignoring:", message);
        return;
      }
      if (text && text.trim()) {
        setMessages((prev) => {
          const existingIndex = prev.findIndex((msg) => msg.id === id);
          if (existingIndex !== -1) {
            return prev.map((msg, idx) =>
              idx === existingIndex
                ? {
                    ...msg,
                    timestamp: message.timestamp || msg.timestamp,
                    data: {
                      ...msg.data,
                      text: text.replace(/\\/g, ""),
                      isStreaming: false,
                      sender: Sender.ASSISTANT,
                    },
                  }
                : msg
            );
          }
          // Insert new
          return [
            ...prev,
            {
              ...message,
              timestamp: message.timestamp || Date.now(),
              data: {
                ...message.data,
                text: text.replace(/\\/g, ""),
                isStreaming: false,
                sender: Sender.ASSISTANT,
              },
            },
          ];
        });
      }
    },

    [MessageType.UPDATE_IN_PROGRESS]: (message: Message) => {
      setIsUpdateInProgress(true);

      const id = message.id;

      setMessages((prev) => {
        if (id) {
          const existingIndex = prev.findIndex((msg) => msg.id === id);
          if (existingIndex !== -1) {
            return prev.map((msg, idx) =>
              idx === existingIndex
                ? {
                    ...msg,
                    timestamp: message.timestamp || msg.timestamp,
                    data: {
                      ...msg.data,
                      text: "Ok - I'll make those changes!",
                      sender: Sender.ASSISTANT,
                    },
                  }
                : msg
            );
          }
        }

        return [
          ...prev,
          {
            ...message,
            timestamp: message.timestamp || Date.now(),
            data: {
              ...message.data,
              text: "Ok - I'll make those changes!",
              sender: Sender.ASSISTANT,
            },
          },
        ];
      });
    },

    [MessageType.UPDATE_FILE]: (message: Message) => {
      const id = message.id;
      if (!id) {
        console.warn("UPDATE_FILE message missing id, ignoring:", message);
        return;
      }
      setMessages((prev) => {
        const existingIndex = prev.findIndex((msg) => msg.id === id);
        if (existingIndex !== -1) {
          return prev.map((msg, idx) =>
            idx === existingIndex
              ? {
                  ...msg,
                  timestamp: message.timestamp || msg.timestamp,
                  data: {
                    ...msg.data,
                    text: message.data.text,
                    sender: Sender.ASSISTANT,
                    isStreaming: true,
                  },
                }
              : msg
          );
        }
        // Insert new
        return [
          ...prev,
          {
            ...message,
            timestamp: message.timestamp || Date.now(),
            data: {
              ...message.data,
              text: message.data.text,
              sender: Sender.ASSISTANT,
              isStreaming: true,
            },
          },
        ];
      });
    },

    [MessageType.UPDATE_COMPLETED]: (message: Message) => {
      setIsUpdateInProgress(false);
      const id = message.id;
      setMessages((prev) => {
        // Remove all UPDATE_FILE messages
        const filtered = prev.filter(
          (msg) => msg.type !== MessageType.UPDATE_FILE
        );

        if (id) {
          const existingIndex = filtered.findIndex((msg) => msg.id === id);
          if (existingIndex !== -1) {
            return filtered.map((msg, idx) =>
              idx === existingIndex
                ? {
                    ...msg,
                    timestamp: message.timestamp || msg.timestamp || Date.now(),
                    data: {
                      ...msg.data,
                      text: "Update completed!",
                      sender: Sender.ASSISTANT,
                    },
                  }
                : msg
            );
          }
        }
        // Insert new
        return [
          ...filtered,
          {
            ...message,
            timestamp: message.timestamp || Date.now(),
            data: {
              ...message.data,
              text: "Update completed!",
              sender: Sender.ASSISTANT,
            },
          },
        ];
      });
      refreshIframe();
    },
  };

  const { isConnected, error, connect, send } = useMessageBus({
    wsUrl: BEAM_CONFIG.WS_URL,
    token: BEAM_CONFIG.TOKEN,
    handlers: messageHandlers,
    onConnect: () => {
      console.log("Connected to Beam Cloud");
    },
    onDisconnect: () => {
      hasConnectedRef.current = false;
    },
    onError: (errorMsg) => {
      console.error("Connection error:", errorMsg);

      let errorString = "Unknown connection error";
      if (typeof errorMsg === "string") {
        errorString = errorMsg;
      } else if (errorMsg && typeof errorMsg === "object") {
        const errorObj = errorMsg as any;
        if (errorObj.message) {
          errorString = String(errorObj.message);
        }
      }

      console.error("Processed error:", errorString);
    },
  });

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (chatHistoryRef.current) {
      chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight;
    }
  }, [messages]);

  // Handle resizing
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isResizing) {
        const newWidth = e.clientX;
        setSidebarWidth(Math.max(300, Math.min(800, newWidth)));
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizing]);

  const handleSendMessage = () => {
    if (inputValue.trim()) {
      send(MessageType.USER, { text: inputValue });
      setInputValue("");
      setMessages((prev) => [
        ...prev,
        {
          type: MessageType.USER,
          timestamp: Date.now(),
          data: {
            text: inputValue,
            sender: Sender.USER,
          },
        },
      ]);
    }
  };

  useEffect(() => {
    if (iframeUrl && isConnected) {
      setIframeError(false);
    }
  }, [iframeUrl, isConnected]);

  const handleIframeLoad = () => {
    console.log("Iframe loaded successfully:", iframeUrl);
    setIframeError(false);
    setIframeReady(true);
  };

  const handleIframeError = () => {
    console.error("Iframe failed to load:", iframeUrl);
    setIframeError(true);
  };

  // Simple auto-connect
  useEffect(() => {
    if (!isConnected && !hasConnectedRef.current) {
      console.log("Connecting to Workspace");
      hasConnectedRef.current = true;
      connect();
    }
  }, [isConnected]);

  // Clear processed message IDs when connection is lost
  useEffect(() => {
    if (!isConnected) {
      processedMessageIds.current.clear();
    }
  }, [isConnected]);

  useEffect(() => {
    setIframeReady(false);
  }, [iframeUrl]);

  useEffect(() => {
    if (
      initCompleted &&
      location.state &&
      location.state.initialPrompt &&
      !initialPromptSent.current
    ) {
      // Send as user message (so it appears in chat)
      send(MessageType.USER, { text: location.state.initialPrompt });
      setMessages((prev) => [
        ...prev,
        {
          type: MessageType.USER,
          timestamp: Date.now(),
          data: {
            text: location.state.initialPrompt,
            sender: Sender.USER,
          },
        },
      ]);
      initialPromptSent.current = true;
    }
  }, [initCompleted, location.state, send, setMessages]);

  const LoadingState = () => (
    <IframeErrorContainer>
      <SpinningIcon icon={faSpinner} size={64} color="gray8" />
      <AnimatedTypography
        variant="textLg"
        color="gray11"
        style={{ marginTop: "24px" }}
      >
        Connecting to Workspace...
      </AnimatedTypography>
      <Typography
        variant="textSm"
        color="gray10"
        style={{ marginTop: "12px", textAlign: "center" }}
      >
        Please wait while we setup your workspace and load the website.
      </Typography>
    </IframeErrorContainer>
  );

  const UpdateInProgressState = () => (
    <IframeErrorContainer>
      <SpinningIcon icon={faSpinner} size={64} color="gray8" />
      <AnimatedTypography
        variant="textLg"
        color="gray11"
        style={{ marginTop: "24px" }}
      >
        Updating Workspace...
      </AnimatedTypography>
      <Typography
        variant="textSm"
        color="gray10"
        style={{ marginTop: "12px", textAlign: "center" }}
      >
        Please wait while we apply your changes to the website.
      </Typography>
    </IframeErrorContainer>
  );

  return (
    <PageContainer>
      <Sidebar style={{ width: `${sidebarWidth}px` }}>
        <BeamHeader>
          <Avatar name="Beam" />
        </BeamHeader>

        <ChatHistory ref={chatHistoryRef}>
          {messages
            .filter((msg) => msg.data.text && msg.data.text.trim())
            .sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0))
            .map((msg, index) => (
              <MessageContainer
                key={msg.id || `msg-${index}-${msg.timestamp || Date.now()}`}
                isUser={msg.data.sender === Sender.USER}
              >
                <MessageBubble isUser={msg.data.sender === Sender.USER}>
                  <Typography
                    variant="textSm"
                    color={msg.data.sender === Sender.USER ? "white" : "gray12"}
                    style={{ whiteSpace: "pre-wrap" }}
                  >
                    {msg.data.text}
                  </Typography>
                  {msg.data.isStreaming && (
                    <TypingIndicator>
                      <TypingDot />
                      <TypingDot />
                      <TypingDot />
                    </TypingIndicator>
                  )}
                </MessageBubble>
              </MessageContainer>
            ))}
        </ChatHistory>

        <ChatInputContainer>
          <ChatInput
            placeholder="Ask Beam..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && handleSendMessage()}
            disabled={!isConnected || !iframeReady}
          />
          <SendButton
            onClick={handleSendMessage}
            disabled={!isConnected || !iframeReady || !inputValue.trim()}
          >
            Send
          </SendButton>
        </ChatInputContainer>
      </Sidebar>

      <ResizeHandle onMouseDown={() => setIsResizing(true)} />

      <MainContent hasIframe={!!iframeUrl}>
        {isConnected ? (
          <IframeContainer>
            <UrlBarContainer>
              <Icon
                icon={faRotateRight}
                size={16}
                color="gray11"
                style={{ cursor: iframeUrl ? "pointer" : "not-allowed" }}
                onClick={iframeUrl ? refreshIframe : undefined}
                title="Refresh"
              />
              <UrlInput value={iframeUrl || ""} readOnly />
              <a
                href={iframeUrl || undefined}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: "flex",
                  alignItems: "center",
                  pointerEvents: iframeUrl ? "auto" : "none",
                }}
                tabIndex={iframeUrl ? 0 : -1}
              >
                <Icon
                  icon={faUpRightFromSquare}
                  size={16}
                  color="gray11"
                  title="Open in new tab"
                />
              </a>
            </UrlBarContainer>
            <IframeArea>
              {iframeError ? (
                <IframeErrorContainer>
                  <Icon icon={faHeart} size={64} color="gray8" />
                  <Typography
                    variant="textLg"
                    color="gray11"
                    style={{ marginTop: "24px" }}
                  >
                    Failed to load website
                  </Typography>
                  <Typography
                    variant="textSm"
                    color="gray10"
                    style={{ marginTop: "12px", textAlign: "center" }}
                  >
                    {iframeUrl} took too long to load or failed to respond.
                  </Typography>
                  <Typography
                    variant="textSm"
                    color="gray10"
                    style={{ marginTop: "8px", textAlign: "center" }}
                  >
                    This could be due to network issues or the website being
                    temporarily unavailable.
                  </Typography>
                </IframeErrorContainer>
              ) : !iframeUrl ? (
                <IframeOverlay>
                  <LoadingState />
                </IframeOverlay>
              ) : !iframeReady || isUpdateInProgress || !initCompleted ? (
                <>
                  <IframeResponsiveWrapper>
                    <WebsiteIframe
                      ref={iframeRef}
                      src={iframeUrl}
                      sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
                      allow="fullscreen"
                      referrerPolicy="no-referrer"
                      loading="lazy"
                      isResizing={isResizing}
                      onLoad={handleIframeLoad}
                      onError={handleIframeError}
                      style={{
                        visibility:
                          iframeReady && !isUpdateInProgress
                            ? "visible"
                            : "hidden",
                        width:
                          typeof DEVICE_SPECS[selectedDevice].width === "number"
                            ? `${DEVICE_SPECS[selectedDevice].width}px`
                            : DEVICE_SPECS[selectedDevice].width,
                        height:
                          typeof DEVICE_SPECS[selectedDevice].height ===
                          "number"
                            ? `${DEVICE_SPECS[selectedDevice].height}px`
                            : DEVICE_SPECS[selectedDevice].height,
                        margin:
                          selectedDevice === "desktop" ? "0" : "24px auto",
                        display: "block",
                        borderRadius: selectedDevice === "desktop" ? 0 : 16,
                        boxShadow:
                          selectedDevice === "desktop"
                            ? "none"
                            : "0 2px 16px rgba(0,0,0,0.12)",
                        background: "#fff",
                        boxSizing: "border-box",
                      }}
                    />
                  </IframeResponsiveWrapper>
                  <IframeOverlay>
                    {isUpdateInProgress || (!iframeReady && !initCompleted) ? (
                      <UpdateInProgressState />
                    ) : (
                      <LoadingState />
                    )}
                  </IframeOverlay>
                </>
              ) : (
                <IframeResponsiveWrapper>
                  <WebsiteIframe
                    ref={iframeRef}
                    src={iframeUrl}
                    sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
                    allow="fullscreen"
                    referrerPolicy="no-referrer"
                    loading="lazy"
                    isResizing={isResizing}
                    onLoad={handleIframeLoad}
                    onError={handleIframeError}
                    style={{
                      visibility:
                        iframeReady && !isUpdateInProgress
                          ? "visible"
                          : "hidden",
                      width:
                        typeof DEVICE_SPECS[selectedDevice].width === "number"
                          ? `${DEVICE_SPECS[selectedDevice].width}px`
                          : DEVICE_SPECS[selectedDevice].width,
                      height:
                        typeof DEVICE_SPECS[selectedDevice].height === "number"
                          ? `${DEVICE_SPECS[selectedDevice].height}px`
                          : DEVICE_SPECS[selectedDevice].height,
                      margin: selectedDevice === "desktop" ? "0" : "24px auto",
                      display: "block",
                      borderRadius: selectedDevice === "desktop" ? 0 : 16,
                      boxShadow:
                        selectedDevice === "desktop"
                          ? "none"
                          : "0 2px 16px rgba(0,0,0,0.12)",
                      background: "#fff",
                      boxSizing: "border-box",
                    }}
                  />
                </IframeResponsiveWrapper>
              )}
            </IframeArea>
            <BottomBar>
              <ToggleGroup>
                <ToggleButton
                  active={true}
                  disabled={
                    !iframeUrl ||
                    !iframeReady ||
                    isUpdateInProgress ||
                    !initCompleted
                  }
                >
                  Preview
                </ToggleButton>
                <ToggleButton
                  active={false}
                  disabled={
                    !iframeUrl ||
                    !iframeReady ||
                    isUpdateInProgress ||
                    !initCompleted
                  }
                >
                  Code
                </ToggleButton>
              </ToggleGroup>
              <DeviceGroup>
                <DeviceButton
                  active={selectedDevice === "mobile"}
                  disabled={
                    !iframeUrl ||
                    !iframeReady ||
                    isUpdateInProgress ||
                    !initCompleted
                  }
                  onClick={() => setSelectedDevice("mobile")}
                >
                  <Icon icon={faMobile} size={18} />
                </DeviceButton>
                <DeviceButton
                  active={selectedDevice === "tablet"}
                  disabled={
                    !iframeUrl ||
                    !iframeReady ||
                    isUpdateInProgress ||
                    !initCompleted
                  }
                  onClick={() => setSelectedDevice("tablet")}
                >
                  <Icon icon={faTablet} size={18} />
                </DeviceButton>
                <DeviceButton
                  active={selectedDevice === "desktop"}
                  disabled={
                    !iframeUrl ||
                    !iframeReady ||
                    isUpdateInProgress ||
                    !initCompleted
                  }
                  onClick={() => setSelectedDevice("desktop")}
                >
                  <Icon icon={faDesktop} size={18} />
                </DeviceButton>
              </DeviceGroup>
              <DeployButton
                disabled={
                  !iframeUrl ||
                  !iframeReady ||
                  isUpdateInProgress ||
                  !initCompleted
                }
              >
                Deploy
              </DeployButton>
            </BottomBar>
          </IframeContainer>
        ) : (
          <>
            <Icon icon={faHeart} size={64} color="gray8" />
            <Typography
              variant="textLg"
              color="gray11"
              style={{ marginTop: "24px" }}
            >
              Connect to start building
            </Typography>

            {error && (
              <ErrorMessage>
                <Typography variant="textSm" color="red">
                  Error: {error}
                </Typography>
              </ErrorMessage>
            )}

            <Checklist>
              <ChecklistItem>
                <Icon icon={faPlay} color="gray10" />
                <Typography variant="textSm" color="gray10">
                  Connect to Workspace
                </Typography>
              </ChecklistItem>
              <ChecklistItem>
                <Icon icon={faPlay} color="gray10" />
                <Typography variant="textSm" color="gray10">
                  Chat with AI in the sidebar
                </Typography>
              </ChecklistItem>
              <ChecklistItem>
                <Icon icon={faPlay} color="gray10" />
                <Typography variant="textSm" color="gray10">
                  Select specific elements to modify
                </Typography>
              </ChecklistItem>
            </Checklist>
          </>
        )}
      </MainContent>
    </PageContainer>
  );
};

export default Create;

const PageContainer = styled.div`
  display: flex;
  flex-direction: row;
  width: 100%;
  height: 100%;
  background-color: ${({ theme }) => theme.colors.gray3};
`;

const Sidebar = styled.div`
  background-color: ${({ theme }) => theme.colors.gray2};
  padding: 24px;
  display: flex;
  flex-direction: column;
  color: white;
  gap: 24px;
`;

const MainContent = styled.div<{ hasIframe: boolean }>`
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  align-items: ${({ hasIframe }) => (hasIframe ? "stretch" : "center")};
  justify-content: ${({ hasIframe }) => (hasIframe ? "stretch" : "center")};
  gap: ${({ hasIframe }) => (hasIframe ? "0" : "24px")};
  background-color: ${({ theme }) => theme.colors.gray1};
`;

const Checklist = styled.div`
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 48px;
`;

const ChecklistItem = styled.div`
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px;
`;

const BeamHeader = styled.div`
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px;
`;

const ChatHistory = styled.div`
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  flex-grow: 1;
`;

const MessageContainer = styled.div<{ isUser: boolean }>`
  display: flex;
  flex-direction: row;
  justify-content: ${({ isUser }) => (isUser ? "flex-end" : "flex-start")};
`;

const MessageBubble = styled.div<{ isUser: boolean }>`
  background-color: ${({ isUser, theme }) =>
    isUser ? theme.colors.blue9 : theme.colors.gray4};
  padding: 12px;
  border-radius: 8px;
  max-width: 70%;
`;

const ChatInputContainer = styled.div`
  margin-top: auto;
  display: flex;
  flex-direction: row;
  gap: 8px;
`;

const ChatInput = styled.input`
  flex-grow: 1;
  background-color: ${({ theme }) => theme.colors.gray1};
  border: 1px solid ${({ theme }) => theme.colors.gray6};
  border-radius: 8px;
  padding: 12px;
  color: ${({ theme }) => theme.colors.gray12};

  &::placeholder {
    color: ${({ theme }) => theme.colors.gray9};
  }
`;

const SendButton = styled.button`
  background-color: ${({ theme }) => theme.colors.blue9};
  color: white;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 14px;

  &:hover:not(:disabled) {
    background-color: ${({ theme }) => theme.colors.blue10};
  }

  &:disabled {
    background-color: ${({ theme }) => theme.colors.gray6};
    cursor: not-allowed;
  }
`;

const ErrorMessage = styled.div`
  background-color: ${({ theme }) => theme.colors.red3};
  border: 1px solid ${({ theme }) => theme.colors.red6};
  border-radius: 6px;
  padding: 12px;
  margin-top: 16px;
`;

const TypingIndicator = styled.div`
  display: flex;
  gap: 4px;
  margin-top: 8px;
  justify-content: flex-start;
`;

const TypingDot = styled.div`
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: ${({ theme }) => theme.colors.gray8};
  animation: typing 1.4s infinite ease-in-out;

  &:nth-child(1) {
    animation-delay: -0.32s;
  }

  &:nth-child(2) {
    animation-delay: -0.16s;
  }

  @keyframes typing {
    0%,
    80%,
    100% {
      transform: scale(0.8);
      opacity: 0.5;
    }
    40% {
      transform: scale(1);
      opacity: 1;
    }
  }
`;

const ResizeHandle = styled.div`
  width: 4px;
  background-color: ${({ theme }) => theme.colors.gray6};
  cursor: col-resize;
  transition: background-color 0.2s ease;

  &:hover {
    background-color: ${({ theme }) => theme.colors.gray8};
  }

  &:active {
    background-color: ${({ theme }) => theme.colors.blue9};
  }
`;

const IframeContainer = styled.div`
  position: relative;
  width: 100%;
  height: 100%;
  overflow: auto;
`;

const IframeArea = styled.div`
  position: relative;
  width: 100%;
  height: calc(100% - 56px - 40px); /* subtract bottom bar and url bar height */
  min-height: 0;
  padding: 0;
  margin: 0;
  box-sizing: border-box;
`;

const IframeResponsiveWrapper = styled.div`
  width: 100%;
  height: 100%;
  overflow: auto;
  display: flex;
  align-items: center;
  justify-content: center;

  & > iframe {
    max-width: 100%;
    max-height: 100%;
  }
`;

const WebsiteIframe = styled.iframe<{ isResizing: boolean }>`
  width: 100%;
  height: 100%;
  border: none;
  pointer-events: ${({ isResizing }) => (isResizing ? "none" : "auto")};
  display: block;
  box-sizing: border-box;
`;

const IframeErrorContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 24px;
`;

const AnimatedTypography = styled(Typography)`
  animation: pulse 1.5s infinite;
  @keyframes pulse {
    0% {
      opacity: 1;
    }
    50% {
      opacity: 0.5;
    }
    100% {
      opacity: 1;
    }
  }
`;

const IframeOverlay = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: ${({ theme }) => theme.colors.gray1};
  z-index: 2;
`;

const SpinningIcon = styled(Icon)`
  animation: spin 1s linear infinite;

  @keyframes spin {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }
`;

const UrlBarContainer = styled.div`
  display: flex;
  align-items: center;
  background: ${({ theme }) => theme.colors.gray2};
  border-bottom: 1px solid ${({ theme }) => theme.colors.gray5};
  padding: 6px 12px;
  gap: 8px;
`;

const UrlInput = styled.input`
  flex: 1;
  background: ${({ theme }) => theme.colors.gray3};
  border: none;
  color: ${({ theme }) => theme.colors.gray11};
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 14px;
  outline: none;
`;

const BottomBar = styled.div`
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: ${({ theme }) => theme.colors.gray2};
  border-top: 1px solid ${({ theme }) => theme.colors.gray5};
  padding: 0 24px;
  height: 56px;
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 3;
`;

const ToggleGroup = styled.div`
  display: flex;
  gap: 8px;
`;

const ToggleButton = styled.button<{ active?: boolean }>`
  background: ${({ active, theme }) =>
    active ? theme.colors.gray4 : theme.colors.gray2};
  color: ${({ active, theme, disabled }) =>
    disabled
      ? theme.colors.gray7
      : active
      ? theme.colors.gray12
      : theme.colors.gray10};
  border: 1px solid ${({ theme }) => theme.colors.gray6};
  border-radius: 6px;
  padding: 6px 18px;
  font-size: 15px;
  font-weight: 500;
  cursor: ${({ disabled }) => (disabled ? "not-allowed" : "pointer")};
  transition: background 0.15s, color 0.15s;
  &:hover:not(:disabled) {
    background: ${({ theme }) => theme.colors.gray5};
  }
`;

const DeviceGroup = styled.div`
  display: flex;
  gap: 8px;
`;

const DeviceButton = styled.button<{ active?: boolean }>`
  background: ${({ active, theme }) =>
    active ? theme.colors.blue9 : theme.colors.gray2};
  color: ${({ active, theme, disabled }) =>
    disabled ? theme.colors.gray7 : active ? "white" : theme.colors.gray10};
  border: 1px solid ${({ theme }) => theme.colors.gray6};
  border-radius: 6px;
  padding: 6px 14px;
  font-size: 14px;
  font-weight: 500;
  cursor: ${({ disabled }) => (disabled ? "not-allowed" : "pointer")};
  transition: background 0.15s, color 0.15s;
  &:hover:not(:disabled) {
    background: ${({ theme }) => theme.colors.blue8};
    color: white;
  }
`;

const DeployButton = styled.button`
  background: ${({ theme }) => theme.colors.violet9};
  color: white;
  border: none;
  border-radius: 6px;
  padding: 8px 28px;
  font-size: 15px;
  font-weight: 600;
  cursor: ${({ disabled }) => (disabled ? "not-allowed" : "pointer")};
  transition: background 0.15s;
  opacity: ${({ disabled }) => (disabled ? 0.6 : 1)};
  &:hover:not(:disabled) {
    background: ${({ theme }) => theme.colors.violet10};
  }
`;
