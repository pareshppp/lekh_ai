import { useState } from 'react'
import { Button } from '~/components/ui/button'
import { Send } from 'lucide-react'
import { interactWithStory } from '~/lib/api'
import { cn } from '~/lib/utils'

interface ChatInputFormProps {
  storyId: string
  disabled?: boolean
  placeholder?: string
  className?: string
}

export function ChatInputForm({ 
  storyId, 
  disabled = false, 
  placeholder = "Send a message...",
  className 
}: ChatInputFormProps) {
  const [message, setMessage] = useState('')
  const [isSending, setIsSending] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!message.trim() || disabled || isSending) return

    try {
      setIsSending(true)
      await interactWithStory(storyId, message.trim())
      setMessage('')
    } catch (error) {
      console.error('Failed to send message:', error)
      // TODO: Show error toast/notification
    } finally {
      setIsSending(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className={cn("flex space-x-2", className)}>
      <div className="flex-1">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder={placeholder}
          disabled={disabled || isSending}
          rows={1}
          className={cn(
            "w-full px-3 py-2 text-sm border rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            "bg-background border-input"
          )}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSubmit(e)
            }
          }}
        />
      </div>
      
      <Button
        type="submit"
        size="icon"
        disabled={!message.trim() || disabled || isSending}
        className="flex-shrink-0"
      >
        {isSending ? (
          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
        ) : (
          <Send className="w-4 h-4" />
        )}
      </Button>
    </form>
  )
}