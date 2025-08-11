import { WebSocketMessage } from '~/lib/hooks/useWebSocket'
import { cn } from '~/lib/utils'
import { Brain, Settings, FileText, HelpCircle, User, CheckCircle, XCircle } from 'lucide-react'

interface AgentStepProps {
  message: WebSocketMessage
  className?: string
}

export function AgentStep({ message, className }: AgentStepProps) {
  const getStepIcon = (type: string) => {
    switch (type) {
      case 'llm_start':
      case 'agent_step':
        return <Brain className="w-4 h-4" />
      case 'tool_start':
      case 'tool_end':
        return <Settings className="w-4 h-4" />
      case 'chain_start':
      case 'chain_end':
        return <FileText className="w-4 h-4" />
      case 'agent_question':
      case 'deviation_proposal':
        return <HelpCircle className="w-4 h-4" />
      case 'user_feedback':
      case 'user_approval':
        return <User className="w-4 h-4" />
      case 'llm_end':
      case 'agent_finish':
        return <CheckCircle className="w-4 h-4" />
      case 'llm_error':
      case 'chain_error':
      case 'tool_error':
      case 'error':
        return <XCircle className="w-4 h-4" />
      default:
        return <FileText className="w-4 h-4" />
    }
  }

  const getStepColor = (type: string) => {
    switch (type) {
      case 'llm_start':
      case 'agent_step':
        return 'text-blue-600 bg-blue-50 border-blue-200 dark:text-blue-400 dark:bg-blue-950/20 dark:border-blue-800'
      case 'tool_start':
      case 'tool_end':
        return 'text-purple-600 bg-purple-50 border-purple-200 dark:text-purple-400 dark:bg-purple-950/20 dark:border-purple-800'
      case 'agent_question':
      case 'deviation_proposal':
        return 'text-amber-600 bg-amber-50 border-amber-200 dark:text-amber-400 dark:bg-amber-950/20 dark:border-amber-800'
      case 'user_feedback':
      case 'user_approval':
        return 'text-green-600 bg-green-50 border-green-200 dark:text-green-400 dark:bg-green-950/20 dark:border-green-800'
      case 'llm_end':
      case 'agent_finish':
        return 'text-green-600 bg-green-50 border-green-200 dark:text-green-400 dark:bg-green-950/20 dark:border-green-800'
      case 'llm_error':
      case 'chain_error':
      case 'tool_error':
      case 'error':
        return 'text-red-600 bg-red-50 border-red-200 dark:text-red-400 dark:bg-red-950/20 dark:border-red-800'
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200 dark:text-gray-400 dark:bg-gray-950/20 dark:border-gray-800'
    }
  }

  const formatTimestamp = (timestamp?: string) => {
    if (!timestamp) return ''
    try {
      const date = new Date(timestamp)
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } catch {
      return ''
    }
  }

  const getMessageTitle = (message: WebSocketMessage) => {
    if (message.agent) {
      return `${message.agent} • ${message.type}`
    }
    return message.type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  return (
    <div className={cn(
      "flex items-start space-x-3 p-3 rounded-lg border transition-colors",
      getStepColor(message.type),
      className
    )}>
      <div className="flex-shrink-0 mt-0.5">
        {getStepIcon(message.type)}
      </div>
      
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-medium truncate">
            {getMessageTitle(message)}
          </h4>
          {message.timestamp && (
            <span className="text-xs opacity-60 ml-2">
              {formatTimestamp(message.timestamp)}
            </span>
          )}
        </div>
        
        <p className="text-sm mt-1 break-words">
          {typeof message.content === 'string' 
            ? message.content 
            : JSON.stringify(message.content)
          }
        </p>
        
        {message.details && (
          <details className="mt-2">
            <summary className="text-xs cursor-pointer opacity-60 hover:opacity-100">
              Show details
            </summary>
            <div className="mt-1 p-2 bg-black/5 dark:bg-white/5 rounded text-xs font-mono whitespace-pre-wrap break-words">
              {message.details}
            </div>
          </details>
        )}
      </div>
    </div>
  )
}