import { useEffect, useRef } from 'react'
import { useWebSocket, WebSocketMessage } from '~/lib/hooks/useWebSocket'
import { AgentStep } from './AgentStep'
import { ChatInputForm } from './ChatInputForm'
import { useLekhStore } from '~/lib/state/store'
import { cn } from '~/lib/utils'

interface AgentActivityFeedProps {
  storyId: string
  className?: string
}

export function AgentActivityFeed({ storyId, className }: AgentActivityFeedProps) {
  const { agentStatus, setAgentStatus } = useLekhStore()
  const scrollRef = useRef<HTMLDivElement>(null)
  
  const { messages, isConnected, connectionStatus } = useWebSocket(storyId, {
    onMessage: (message: WebSocketMessage) => {
      // Update agent status based on message type
      if (message.type === 'agent_step' || message.type === 'llm_start') {
        setAgentStatus('generating')
      } else if (message.type === 'agent_question') {
        setAgentStatus('awaiting_user_input')
      } else if (message.type === 'llm_end' || message.type === 'agent_finish') {
        setAgentStatus('idle')
      }
    },
    onConnect: () => {
      console.log('WebSocket connected for story:', storyId)
    },
    onDisconnect: () => {
      console.log('WebSocket disconnected for story:', storyId)
      setAgentStatus('disconnected')
    },
    onError: (error) => {
      console.error('WebSocket error:', error)
      setAgentStatus('error')
    }
  })

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const getConnectionStatusMessage = () => {
    switch (connectionStatus) {
      case 'connecting':
        return 'Connecting to story updates...'
      case 'connected':
        return null // Don't show message when connected
      case 'error':
        return 'Connection error. Trying to reconnect...'
      case 'disconnected':
        return 'Disconnected from story updates.'
      default:
        return null
    }
  }

  const connectionMessage = getConnectionStatusMessage()

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {/* Header */}
      <div className="p-4 border-b">
        <h2 className="font-semibold text-lg">Control Tower</h2>
        <div className="flex items-center space-x-2 mt-1">
          <div className={cn(
            "w-2 h-2 rounded-full",
            isConnected ? "bg-green-500" : "bg-red-500"
          )} />
          <span className="text-sm text-muted-foreground">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Activity Feed */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-3"
      >
        {connectionMessage && (
          <div className="flex items-center justify-center p-4 text-sm text-muted-foreground bg-muted/50 rounded-lg">
            {connectionMessage}
          </div>
        )}

        {messages.length === 0 && isConnected && (
          <div className="flex items-center justify-center p-8 text-center">
            <div className="space-y-2">
              <div className="text-2xl">🤖</div>
              <p className="text-sm text-muted-foreground">
                Waiting for agent activity...
              </p>
            </div>
          </div>
        )}

        {messages.map((message, index) => (
          <AgentStep key={index} message={message} />
        ))}

        {agentStatus === 'generating' && (
          <div className="flex items-center space-x-2 p-3 bg-blue-50 dark:bg-blue-950/20 rounded-lg">
            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm text-blue-700 dark:text-blue-300">
              Agent is working...
            </span>
          </div>
        )}
      </div>

      {/* Input Form */}
      <div className="p-4 border-t">
        <ChatInputForm 
          storyId={storyId} 
          disabled={agentStatus === 'generating' || !isConnected}
          placeholder={
            agentStatus === 'awaiting_user_input' 
              ? "The agent is waiting for your input..."
              : agentStatus === 'generating'
              ? "Agent is working..."
              : "Send a message to the agent..."
          }
        />
      </div>
    </div>
  )
}