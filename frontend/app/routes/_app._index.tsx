import { useState } from 'react'
import { json, redirect, type LoaderFunctionArgs, type ActionFunctionArgs, type MetaFunction } from '@remix-run/node'
import { useLoaderData, useNavigate, Form } from '@remix-run/react'
import { supabase } from '~/lib/supabase'
import { getStories, createStory, deleteStories, type Story, type CreateStoryRequest } from '~/lib/api'
import { Button } from '~/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card'
import { Header } from '~/components/layout/Header'
import { Plus, Calendar, Clock, Trash2 } from 'lucide-react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '~/components/ui/dialog'
import { Label } from '~/components/ui/label'
import { Input } from '~/components/ui/input'
import { Textarea } from '~/components/ui/textarea'
import { Checkbox } from '~/components/ui/checkbox'

export const meta: MetaFunction = () => {
  return [
    { title: "Dashboard | Lekh AI" },
    { name: "description", content: "Your story dashboard - create and manage AI-generated stories" },
  ]
}

export async function loader({ request }: LoaderFunctionArgs) {
  const { data: { session } } = await supabase.auth.getSession()
  
  if (!session) {
    return redirect('/login')
  }

  try {
    const stories = await getStories()
    return json({ 
      user: session.user,
      stories,
      error: null
    })
  } catch (error) {
    console.error('Failed to load stories:', error)
    return json({ 
      user: session.user,
      stories: [],
      error: 'Failed to load stories'
    })
  }
}

export async function action({ request }: ActionFunctionArgs) {
  const { data: { session } } = await supabase.auth.getSession()
  
  if (!session) {
    return redirect('/login')
  }

  const formData = await request.formData()
  const action = formData.get('action')

  if (action === 'create_story') {
    try {
      const prompt = formData.get('prompt') as string
      const title = formData.get('title') as string
      const genresString = formData.get('genres') as string
      const genres = genresString ? genresString.split(',').map(g => g.trim()) : []

      const createRequest: CreateStoryRequest = {
        prompt,
        genres,
        title: title || undefined
      }

      const result = await createStory(createRequest)
      return redirect(`/story/${result.story_id}`)
    } catch (error) {
      console.error('Failed to create story:', error)
      return json({ error: 'Failed to create story' }, { status: 500 })
    }
  }

  if (action === 'delete_stories') {
    try {
      const storyIds = formData.getAll('storyIds') as string[]
      await deleteStories(storyIds)
      return json({ success: true })
    } catch (error) {
      console.error('Failed to delete stories:', error)
      return json({ error: 'Failed to delete stories' }, { status: 500 })
    }
  }

  return json({ error: 'Unknown action' }, { status: 400 })
}

const GENRE_OPTIONS = [
  'Fantasy', 'Science Fiction', 'Mystery', 'Thriller', 'Romance', 
  'Horror', 'Adventure', 'Historical Fiction', 'Literary Fiction', 
  'Young Adult', 'Children\'s', 'Comedy', 'Drama'
]

export default function Dashboard() {
  const { user, stories, error } = useLoaderData<typeof loader>()
  const navigate = useNavigate()
  const [selectedStories, setSelectedStories] = useState<Set<string>>(new Set())
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [selectedGenres, setSelectedGenres] = useState<Set<string>>(new Set())

  const handleStoryClick = (storyId: string) => {
    navigate(`/story/${storyId}`)
  }

  const handleSelectStory = (storyId: string, checked: boolean) => {
    const newSelected = new Set(selectedStories)
    if (checked) {
      newSelected.add(storyId)
    } else {
      newSelected.delete(storyId)
    }
    setSelectedStories(newSelected)
  }

  const handleSelectAll = () => {
    if (selectedStories.size === stories.length) {
      setSelectedStories(new Set())
    } else {
      setSelectedStories(new Set(stories.map(s => s.id)))
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'writing_complete':
        return 'text-green-600 bg-green-100'
      case 'initializing':
      case 'generating':
        return 'text-blue-600 bg-blue-100'
      case 'awaiting_user_input':
      case 'awaiting_user_approval':
        return 'text-amber-600 bg-amber-100'
      case 'error':
        return 'text-red-600 bg-red-100'
      default:
        return 'text-gray-600 bg-gray-100'
    }
  }

  const formatStatus = (status: string) => {
    return status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  return (
    <div className="min-h-screen bg-background">
      <Header user={user} />
      
      <div className="container mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">Your Stories</h1>
            <p className="text-muted-foreground mt-1">
              Create and manage your AI-generated stories
            </p>
          </div>

          <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="w-4 h-4 mr-2" />
                New Story
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle>Create New Story</DialogTitle>
                <DialogDescription>
                  Provide a prompt and select genres for your AI-generated story.
                </DialogDescription>
              </DialogHeader>
              <Form method="post" className="space-y-4" onSubmit={() => setIsCreateDialogOpen(false)}>
                <input type="hidden" name="action" value="create_story" />
                
                <div className="space-y-2">
                  <Label htmlFor="title">Title (Optional)</Label>
                  <Input 
                    id="title" 
                    name="title" 
                    placeholder="Enter a title for your story..."
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="prompt">Story Prompt</Label>
                  <Textarea
                    id="prompt"
                    name="prompt"
                    placeholder="Describe the story you want to create..."
                    required
                    rows={4}
                  />
                </div>

                <div className="space-y-3">
                  <Label>Genres (Select 1-3)</Label>
                  <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                    {GENRE_OPTIONS.map((genre) => (
                      <div key={genre} className="flex items-center space-x-2">
                        <Checkbox
                          id={genre}
                          checked={selectedGenres.has(genre)}
                          onCheckedChange={(checked) => {
                            const newGenres = new Set(selectedGenres)
                            if (checked) {
                              if (newGenres.size < 3) {
                                newGenres.add(genre)
                              }
                            } else {
                              newGenres.delete(genre)
                            }
                            setSelectedGenres(newGenres)
                          }}
                          disabled={!selectedGenres.has(genre) && selectedGenres.size >= 3}
                        />
                        <Label htmlFor={genre} className="text-sm">
                          {genre}
                        </Label>
                      </div>
                    ))}
                  </div>
                  <input 
                    type="hidden" 
                    name="genres" 
                    value={Array.from(selectedGenres).join(',')} 
                  />
                </div>

                <div className="flex justify-end space-x-2">
                  <Button type="button" variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={selectedGenres.size === 0}>
                    Create Story
                  </Button>
                </div>
              </Form>
            </DialogContent>
          </Dialog>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        {/* Bulk Actions */}
        {selectedStories.size > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <div className="flex items-center justify-between">
              <span className="text-sm text-blue-700">
                {selectedStories.size} story{selectedStories.size > 1 ? 's' : ''} selected
              </span>
              <Form method="post">
                <input type="hidden" name="action" value="delete_stories" />
                {Array.from(selectedStories).map(id => (
                  <input key={id} type="hidden" name="storyIds" value={id} />
                ))}
                <Button type="submit" variant="destructive" size="sm">
                  <Trash2 className="w-4 h-4 mr-2" />
                  Delete Selected
                </Button>
              </Form>
            </div>
          </div>
        )}

        {/* Stories Grid */}
        {stories.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">📚</div>
            <h3 className="text-xl font-semibold mb-2">No stories yet</h3>
            <p className="text-muted-foreground mb-6">
              Create your first AI-generated story to get started.
            </p>
            <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="w-4 h-4 mr-2" />
                  Create Your First Story
                </Button>
              </DialogTrigger>
              {/* Dialog content same as above */}
            </Dialog>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Select All */}
            <div className="flex items-center space-x-2 pb-2 border-b">
              <Checkbox
                checked={selectedStories.size === stories.length && stories.length > 0}
                onCheckedChange={handleSelectAll}
              />
              <Label className="text-sm text-muted-foreground">
                Select all stories
              </Label>
            </div>

            {/* Stories List */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {stories.map((story: Story) => (
                <Card key={story.id} className="hover:shadow-md transition-shadow cursor-pointer">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          checked={selectedStories.has(story.id)}
                          onCheckedChange={(checked) => handleSelectStory(story.id, checked as boolean)}
                          onClick={(e) => e.stopPropagation()}
                        />
                        <CardTitle 
                          className="text-lg truncate cursor-pointer" 
                          onClick={() => handleStoryClick(story.id)}
                        >
                          {story.title}
                        </CardTitle>
                      </div>
                      <span className={`text-xs px-2 py-1 rounded-full ${getStatusColor(story.system_status)}`}>
                        {formatStatus(story.system_status)}
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent onClick={() => handleStoryClick(story.id)}>
                    <div className="flex items-center justify-between text-sm text-muted-foreground">
                      <div className="flex items-center space-x-4">
                        <div className="flex items-center space-x-1">
                          <Calendar className="w-4 h-4" />
                          <span>{formatDate(story.created_at)}</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <Clock className="w-4 h-4" />
                          <span>{formatDate(story.updated_at)}</span>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}