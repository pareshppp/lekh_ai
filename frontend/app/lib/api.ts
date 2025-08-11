import { supabase } from './supabase'

const API_BASE_URL = process.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

class APIError extends Error {
  constructor(message: string, public status: number) {
    super(message)
    this.name = 'APIError'
  }
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  const { data: { session } } = await supabase.auth.getSession()
  
  if (!session?.access_token) {
    throw new APIError('No authentication token available', 401)
  }

  return {
    'Authorization': `Bearer ${session.access_token}`,
    'Content-Type': 'application/json',
  }
}

async function apiRequest<T>(
  endpoint: string, 
  options: RequestInit = {}
): Promise<T> {
  const headers = await getAuthHeaders()
  
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      ...headers,
      ...options.headers,
    },
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new APIError(
      errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
      response.status
    )
  }

  return response.json()
}

// Story API functions
export interface Story {
  id: string
  title: string
  created_at: string
  updated_at: string
  system_status: string
}

export interface CreateStoryRequest {
  prompt: string
  genres: string[]
  title?: string
}

export interface UserInteractionRequest {
  message: string
}

export async function getStories(): Promise<Story[]> {
  return apiRequest<Story[]>('/stories')
}

export async function createStory(request: CreateStoryRequest): Promise<{ story_id: string; title: string; status: string }> {
  return apiRequest('/stories', {
    method: 'POST',
    body: JSON.stringify(request),
  })
}

export async function deleteStories(storyIds: string[]): Promise<{ deleted_count: number; errors: string[] }> {
  return apiRequest('/stories', {
    method: 'DELETE',
    body: JSON.stringify({ story_ids: storyIds }),
  })
}

export async function getStoryDetails(storyId: string): Promise<any> {
  return apiRequest(`/stories/${storyId}`)
}

export async function interactWithStory(storyId: string, message: string): Promise<{ message: string }> {
  return apiRequest(`/stories/${storyId}/interact`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  })
}

export async function getStoryOutline(storyId: string): Promise<any> {
  return apiRequest(`/stories/${storyId}/outline`)
}

export async function getStoryContent(storyId: string, nodeId: string): Promise<any> {
  return apiRequest(`/stories/${storyId}/content/${nodeId}`)
}

export async function getStoryBibleCategory(storyId: string, category: string): Promise<{ category: string; items: any[] }> {
  return apiRequest(`/stories/${storyId}/bible/${category}`)
}

export { APIError }