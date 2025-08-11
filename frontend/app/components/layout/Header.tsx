import { useState } from 'react'
import { Form, Link } from '@remix-run/react'
import { Button } from '~/components/ui/button'
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuTrigger,
  DropdownMenuSeparator
} from '~/components/ui/dropdown-menu'
import { Download, User, LogOut } from 'lucide-react'
import { useLekhStore } from '~/lib/state/store'
import type { User as SupabaseUser } from '@supabase/supabase-js'

interface HeaderProps {
  user: SupabaseUser | null
  storyTitle?: string
  storyId?: string
}

export function Header({ user, storyTitle, storyId }: HeaderProps) {
  const [isDownloading, setIsDownloading] = useState(false)
  const { currentStoryId } = useLekhStore()

  const handleDownload = async () => {
    if (!storyId) return
    
    try {
      setIsDownloading(true)
      // TODO: Implement download functionality
      // const response = await downloadStoryAsMarkdown(storyId)
      // Create and trigger download
      console.log('Download functionality to be implemented')
    } catch (error) {
      console.error('Failed to download story:', error)
    } finally {
      setIsDownloading(false)
    }
  }

  return (
    <header className="h-16 border-b bg-background flex items-center justify-between px-6">
      <div className="flex items-center space-x-4">
        <Link to="/" className="text-xl font-bold text-primary">
          Lekh AI
        </Link>
        {storyTitle && (
          <>
            <span className="text-muted-foreground">/</span>
            <h1 className="text-lg font-semibold truncate max-w-xs">
              {storyTitle}
            </h1>
          </>
        )}
      </div>

      <div className="flex items-center space-x-4">
        {storyId && (
          <Button 
            variant="outline" 
            size="sm"
            onClick={handleDownload}
            disabled={isDownloading}
          >
            <Download className="w-4 h-4 mr-2" />
            {isDownloading ? 'Downloading...' : 'Download'}
          </Button>
        )}

        {user && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" className="flex items-center space-x-2">
                <User className="w-4 h-4" />
                <span className="hidden sm:inline-block truncate max-w-32">
                  {user.email}
                </span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <div className="px-3 py-2 text-sm">
                <p className="font-medium">Signed in as</p>
                <p className="text-muted-foreground truncate">{user.email}</p>
              </div>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link to="/dashboard" className="cursor-pointer">
                  Dashboard
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Form method="post" action="/auth/logout">
                  <button type="submit" className="flex items-center w-full cursor-pointer">
                    <LogOut className="w-4 h-4 mr-2" />
                    Sign out
                  </button>
                </Form>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </header>
  )
}