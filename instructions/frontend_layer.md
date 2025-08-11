Of course. Here is a highly detailed design plan for the "Lekh" frontend, tailored for a coding agent. It incorporates the full conversation history and the requested shift to a Supabase and Neo4j Aura cloud stack.

---

### **Project "Lekh": Frontend Detailed Design Plan**

**Objective:** To create the frontend for "Lekh," a collaborative story-writing application. The frontend is a rich, interactive single-page application that serves as the user's "Integrated Development Environment (IDE)" for creating novels with an AI agent partner.

**Target Audience:** This document is for a coding agent. It assumes the agent is proficient in **React, TypeScript, Remix, and Tailwind CSS**.

**Core Technologies:**
*   **Framework:** Remix
*   **Language:** TypeScript
*   **Styling:** Tailwind CSS
*   **UI Components:** Shadcn/UI (for pre-built, accessible components like buttons, dialogs, tabs)
*   **State Management:** Remix loaders/actions for server state; `zustand` for client-side state (e.g., managing UI state, active WebSocket connections).
*   **Rich Text Editor:** Tiptap
*   **Graph Visualization:** A React library like `react-flow` or `vis.js` (wrapped in a React component). `react-flow` is preferred for its declarative nature.
*   **Authentication:** Supabase Auth UI

---

### **1. Cloud Backend Integration (Critical Context for the Frontend)**

The frontend will not interact with databases directly. It will communicate with a cloud-based ecosystem:

*   **Authentication & User Management:** Handled by **Supabase Auth**. The frontend will use Supabase's client library (`@supabase/auth-ui-react`, `@supabase/supabase-js`) for login, signup, and session management.
*   **API & Agent Orchestration:** A **FastAPI Backend** (running locally on docker container). The frontend will send all API requests to this backend. It will receive a JWT from Supabase and include it as a Bearer token in the `Authorization` header of every API call to the FastAPI backend.
*   **Real-time Agent Streaming:** The frontend will establish a **WebSocket** connection to the FastAPI backend to receive real-time updates from the agent.
*   **Database (Implicit):** The frontend does *not* need to know about Neo4j Aura. It only needs to know that the FastAPI backend provides endpoints to get and update story data.

---

### **2. Directory & Component Structure**

Create a Remix project and structure it as follows:

`frontend/`
```
├── app/
│   ├── components/
│   │   ├── # UI Primitives (from Shadcn/UI)
│   │   │   ├── ui/
│   │   │   │   ├── button.tsx, card.tsx, dialog.tsx, tabs.tsx, ...
│   │   ├── # Core Application Layout
│   │   │   ├── layout/
│   │   │   │   ├── AppLayout.tsx           # The main 3-pane responsive layout
│   │   │   │   └── Header.tsx              # Top bar with user menu & actions
│   │   ├── # Agent Interaction Components
│   │   │   ├── chat/
│   │   │   │   ├── AgentActivityFeed.tsx   # Main component for the chat pane
│   │   │   │   ├── AgentStep.tsx           # Renders 🧠, ⚙️, 📋, ❓ steps
│   │   │   │   └── ChatInputForm.tsx       # The form for sending messages
│   │   ├── # Story Structure & Content Components
│   │   │   ├── story/
│   │   │   │   ├── StoryOutline.tsx        # The expandable tree view ToC
│   │   │   │   ├── CanvasEditor.tsx        # Tiptap rich text editor component
│   │   │   │   └── StoryBiblePane.tsx      # Tabbed pane for Bible exploration
│   │   ├── # Data Visualization Components
│   │   │   └── graph/
│   │   │       └── KnowledgeGraphExplorer.tsx # Component using react-flow
│   ├── lib/
│   │   ├── api.ts          # Client-side functions for calling the FastAPI backend
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts # Custom hook to manage the WebSocket connection
│   │   ├── state/
│   │   │   └── store.ts      # Zustand store for global client state
│   │   └── supabase.ts     # Supabase client initialization
│   ├── routes/
│   │   ├── _auth.login.tsx   # Login page
│   │   ├── _auth.callback.tsx# OAuth callback handler
│   │   ├── _app._index.tsx   # Dashboard/Homepage showing list of stories
│   │   └── _app.story.$storyId.tsx # The main story editing page
│   └── root.tsx            # Root layout, includes global styles
├── public/
├── package.json
└── tsconfig.json
```

---

### **3. Detailed Component & Feature Implementation Plan**

#### **3.1. Authentication (`/routes/_auth.*.tsx`, `/lib/supabase.ts`)**

1.  **Initialize Supabase Client:** In `/lib/supabase.ts`, create and export a Supabase client instance using environment variables (`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`).
2.  **Login Page (`_auth.login.tsx`):**
    *   Implement the `@supabase/auth-ui-react` `Auth` component.
    *   Configure it for providers like Google, GitHub, and email/password.
    *   Use the "dark" theme from `@supabase/auth-ui-shared`.
    *   On successful login, Supabase handles session cookies. The user should be redirected to the app's home (`/`).
3.  **Session Management:** In the `root.tsx` loader, check for an active Supabase session. If no session exists, redirect to `/login`. Pass the session data to child routes.

#### **3.2. Main Application Layout (`/routes/_app.story.$storyId.tsx`, `/components/layout/`)**

1.  **`AppLayout.tsx`:**
    *   Use CSS Grid to create a responsive 3-pane layout.
    *   **Left Pane:** Fixed width (e.g., `350px`).
    *   **Center Pane:** Flexible width (`1fr`).
    *   **Right Pane:** Fixed width (e.g., `400px`).
    *   On smaller screens (e.g., tablets), the right pane should become a collapsible drawer. On mobile, all panes should stack or be tabbed.
2.  **`Header.tsx`:**
    *   Display the current Story Title.
    *   Include a "Download as Markdown" button. `onClick`, it should call an API function from `/lib/api.ts` that hits the `GET /api/story/{story_id}/download` endpoint.
    *   Include a user dropdown menu showing the user's email, with a "Sign Out" option that calls Supabase's `signOut()` method.

#### **3.3. Left Pane: Control Tower**

1.  **`AgentActivityFeed.tsx`:**
    *   This component will display a vertical list of agent activity messages.
    *   It will get its data from a custom hook `useWebSocket('/api/story/{story_id}/stream')`.
    *   The hook will manage the WebSocket connection and return an array of message objects.
    *   The component will map over this array and pass each message to `AgentStep.tsx`.
    *   It should automatically scroll to the bottom as new messages arrive.
2.  **`AgentStep.tsx`:**
    *   This component receives a single message object (e.g., `{ type: 'thought', content: '...' }`).
    *   It will use a `switch` statement on `message.type` to render the correct visual representation (icon, styling) for "thought", "tool_call", "tool_result", "agent_question", etc.
3.  **`ChatInputForm.tsx`:**
    *   A simple form with a text input and a "Send" button.
    *   On submit, it will call an API function from `/lib/api.ts` that makes a `POST` request to `/api/story/{story_id}/interact` with the message content.
    *   The input should be disabled when the agent's `system_status` is not awaiting user input.

#### **3.4. Center Pane: The Canvas**

1.  **`StoryOutline.tsx` (Top of Center Pane):**
    *   This is the expandable Table of Contents.
    *   **Data Source:** The `loader` for the `_app.story.$storyId.tsx` route will fetch the full story hierarchy from the backend (`GET /api/story/{story_id}/outline`).
    *   **Implementation:** Use a recursive component or a library like `react-arborist` to render the tree structure (`Arc` -> `Chapter` -> `Scene`).
    *   **Interactivity:**
        *   Each item in the tree is a button or link.
        *   Clicking an item (e.g., a Scene) should update a piece of client-side state (in the Zustand store) indicating the `activeNodeId`.
2.  **`CanvasEditor.tsx` (Bottom of Center Pane):**
    *   **Data Source:** This component will subscribe to the `activeNodeId` from the Zustand store. When it changes, it will fetch the content for that node from the backend (`GET /api/story/{story_id}/content/{activeNodeId}`).
    *   **Implementation:**
        *   Integrate the Tiptap rich text editor.
        *   Display a loading state while fetching content.
        *   Display a placeholder if no node is selected.
    *   **Saving:**
        *   Provide an explicit "Save Changes" button.
        *   `onClick`, it should get the editor's content (as HTML or Markdown) and call an API function to `PUT` the data to `/api/story/{story_id}/content/{activeNodeId}`.
        *   Implement an auto-save feature using a debounce function that triggers the save logic after the user stops typing for 2-3 seconds.

#### **3.5. Right Pane: Story Bible & Graph Explorer**

1.  **`StoryBiblePane.tsx`:**
    *   Use the `Tabs` component from Shadcn/UI.
    *   Create tabs: "Characters", "Locations", "Items", "Graph".
    *   Each tab's content will fetch its data from the API (e.g., `GET /api/story/{story_id}/bible/character`).
    *   Display items in a searchable list. Clicking an item should set the `activeNodeId` in the Zustand store, causing the `CanvasEditor` to load its content.
2.  **`KnowledgeGraphExplorer.tsx` (in the "Graph" tab):**
    *   **Data Source:** Fetch graph data from `GET /api/story/{story_id}/graph_data`. The data should be in a format `react-flow` expects: an array of `nodes` and an array of `edges`.
    *   **Implementation:**
        *   Use `react-flow` to render the graph.
        *   Implement a layout algorithm (e.g., Dagre) to automatically position nodes neatly.
        *   Style nodes differently based on their `type` property (`Character`, `Scene`, etc.).
        *   Add controls for panning, zooming, and filtering (checkboxes to toggle node/edge types).

---

### **4. Global State Management (Zustand)**

Create a store in `/lib/state/store.ts`. It will manage UI state that needs to be shared across non-parent/child components.

**Store State:**
```typescript
interface LekhStore {
  // The ID of the node currently displayed in the CanvasEditor
  activeNodeId: string | null;
  setActiveNodeId: (id: string | null) => void;

  // The current status of the agent, to enable/disable UI elements
  agentStatus: string; // e.g., 'generating', 'awaiting_user_input'
  setAgentStatus: (status: string) => void;

  // Full story outline for the ToC
  storyOutline: StoryHierarchy | null;
  setStoryOutline: (outline: StoryHierarchy) => void;
}
```

### Docker

This frontend will run on a local docker container and connected with the rest of the app using docker compose.

This detailed plan provides the coding agent with a clear blueprint, specifying the architecture, component breakdown, data flow, and key features required to build the "Lekh" frontend.