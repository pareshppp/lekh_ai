import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

export interface StoryHierarchy {
  story: any
  arcs: any[]
  chapters: any[]
  scenes: any[]
}

interface LekhStore {
  // UI State
  activeNodeId: string | null
  setActiveNodeId: (id: string | null) => void

  // Agent Status
  agentStatus: string
  setAgentStatus: (status: string) => void

  // Story Outline
  storyOutline: StoryHierarchy | null
  setStoryOutline: (outline: StoryHierarchy | null) => void

  // Current story being viewed
  currentStoryId: string | null
  setCurrentStoryId: (id: string | null) => void

  // Loading states
  isLoadingContent: boolean
  setIsLoadingContent: (loading: boolean) => void

  // Selected content
  selectedContent: any
  setSelectedContent: (content: any) => void

  // Sidebar visibility (mobile)
  isLeftSidebarOpen: boolean
  isRightSidebarOpen: boolean
  setLeftSidebarOpen: (open: boolean) => void
  setRightSidebarOpen: (open: boolean) => void

  // Error state
  error: string | null
  setError: (error: string | null) => void

  // Clear all state (for logout, etc.)
  clearState: () => void
}

export const useLekhStore = create<LekhStore>()(
  devtools(
    (set, get) => ({
      // UI State
      activeNodeId: null,
      setActiveNodeId: (id) => set({ activeNodeId: id }),

      // Agent Status
      agentStatus: 'idle',
      setAgentStatus: (status) => set({ agentStatus: status }),

      // Story Outline
      storyOutline: null,
      setStoryOutline: (outline) => set({ storyOutline: outline }),

      // Current story
      currentStoryId: null,
      setCurrentStoryId: (id) => set({ currentStoryId: id }),

      // Loading states
      isLoadingContent: false,
      setIsLoadingContent: (loading) => set({ isLoadingContent: loading }),

      // Selected content
      selectedContent: null,
      setSelectedContent: (content) => set({ selectedContent: content }),

      // Sidebar visibility
      isLeftSidebarOpen: false,
      isRightSidebarOpen: false,
      setLeftSidebarOpen: (open) => set({ isLeftSidebarOpen: open }),
      setRightSidebarOpen: (open) => set({ isRightSidebarOpen: open }),

      // Error state
      error: null,
      setError: (error) => set({ error }),

      // Clear state
      clearState: () => set({
        activeNodeId: null,
        agentStatus: 'idle',
        storyOutline: null,
        currentStoryId: null,
        isLoadingContent: false,
        selectedContent: null,
        isLeftSidebarOpen: false,
        isRightSidebarOpen: false,
        error: null,
      }),
    }),
    {
      name: 'lekh-store',
    }
  )
)