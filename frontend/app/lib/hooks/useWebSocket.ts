import { useEffect, useState, useCallback, useRef } from 'react'
import { supabase } from '../supabase'

export interface WebSocketMessage {
  type: string
  content: string
  timestamp?: string
  agent?: string
  details?: string
  story_id?: string
}

interface UseWebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: Event) => void
}

export function useWebSocket(storyId: string, options: UseWebSocketOptions = {}) {
  const [isConnected, setIsConnected] = useState(false)
  const [messages, setMessages] = useState<WebSocketMessage[]>([])
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected')
  
  const websocketRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 5

  const connect = useCallback(async () => {
    if (websocketRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    try {
      setConnectionStatus('connecting')
      
      // Get current session for auth
      const { data: { session } } = await supabase.auth.getSession()
      
      if (!session?.access_token) {
        throw new Error('No authentication token available')
      }

      const wsUrl = process.env.VITE_WS_BASE_URL || 'ws://localhost:8000'
      const ws = new WebSocket(`${wsUrl}/ws/stories/${storyId}`)
      
      ws.onopen = async () => {
        // Send authentication message
        ws.send(JSON.stringify({
          type: 'auth',
          token: session.access_token
        }))
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          
          if (message.type === 'auth_success') {
            setIsConnected(true)
            setConnectionStatus('connected')
            reconnectAttempts.current = 0
            options.onConnect?.()
          } else if (message.type === 'auth_error' || message.type === 'access_error') {
            console.error('WebSocket auth error:', message.content)
            setConnectionStatus('error')
            ws.close()
          } else {
            // Handle regular messages
            setMessages(prev => [...prev, message])
            options.onMessage?.(message)
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      ws.onclose = (event) => {
        setIsConnected(false)
        setConnectionStatus('disconnected')
        websocketRef.current = null
        options.onDisconnect?.()

        // Attempt to reconnect if not a clean close
        if (!event.wasClean && reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.pow(2, reconnectAttempts.current) * 1000 // Exponential backoff
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++
            connect()
          }, delay)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setConnectionStatus('error')
        options.onError?.(error)
      }

      websocketRef.current = ws

    } catch (error) {
      console.error('Failed to connect WebSocket:', error)
      setConnectionStatus('error')
    }
  }, [storyId, options])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    
    if (websocketRef.current) {
      websocketRef.current.close(1000, 'User initiated disconnect')
      websocketRef.current = null
    }
    
    setIsConnected(false)
    setConnectionStatus('disconnected')
    reconnectAttempts.current = 0
  }, [])

  const sendMessage = useCallback((message: any) => {
    if (websocketRef.current?.readyState === WebSocket.OPEN) {
      websocketRef.current.send(JSON.stringify(message))
    }
  }, [])

  const clearMessages = useCallback(() => {
    setMessages([])
  }, [])

  // Connect when component mounts or storyId changes
  useEffect(() => {
    if (storyId) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [storyId, connect, disconnect])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [])

  return {
    isConnected,
    connectionStatus,
    messages,
    connect,
    disconnect,
    sendMessage,
    clearMessages,
  }
}