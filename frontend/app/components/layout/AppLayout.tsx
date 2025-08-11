import { ReactNode } from 'react'
import { cn } from '~/lib/utils'
import { useLekhStore } from '~/lib/state/store'
import { Button } from '~/components/ui/button'
import { Menu, X } from 'lucide-react'

interface AppLayoutProps {
  children: ReactNode
  leftPane: ReactNode
  rightPane: ReactNode
  className?: string
}

export function AppLayout({ children, leftPane, rightPane, className }: AppLayoutProps) {
  const { 
    isLeftSidebarOpen, 
    isRightSidebarOpen, 
    setLeftSidebarOpen, 
    setRightSidebarOpen 
  } = useLekhStore()

  return (
    <div className={cn("h-screen flex flex-col", className)}>
      {/* Mobile header with hamburger menus */}
      <div className="lg:hidden flex items-center justify-between p-4 border-b">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setLeftSidebarOpen(!isLeftSidebarOpen)}
          className="lg:hidden"
        >
          <Menu className="h-5 w-5" />
        </Button>
        
        <h1 className="font-semibold">Lekh AI</h1>
        
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setRightSidebarOpen(!isRightSidebarOpen)}
          className="lg:hidden"
        >
          <Menu className="h-5 w-5" />
        </Button>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Left Pane */}
        <div className={cn(
          "fixed inset-y-0 left-0 z-50 w-80 border-r bg-background transition-transform duration-200 ease-in-out lg:relative lg:translate-x-0 lg:z-auto",
          isLeftSidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}>
          <div className="flex items-center justify-between p-4 border-b lg:hidden">
            <h2 className="font-semibold">Control Tower</h2>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setLeftSidebarOpen(false)}
            >
              <X className="h-5 w-5" />
            </Button>
          </div>
          <div className="flex-1 overflow-y-auto">
            {leftPane}
          </div>
        </div>

        {/* Mobile overlay */}
        {(isLeftSidebarOpen || isRightSidebarOpen) && (
          <div 
            className="fixed inset-0 z-40 bg-black/50 lg:hidden" 
            onClick={() => {
              setLeftSidebarOpen(false)
              setRightSidebarOpen(false)
            }}
          />
        )}

        {/* Center Pane */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {children}
        </div>

        {/* Right Pane */}
        <div className={cn(
          "fixed inset-y-0 right-0 z-50 w-96 border-l bg-background transition-transform duration-200 ease-in-out lg:relative lg:translate-x-0 lg:z-auto",
          isRightSidebarOpen ? "translate-x-0" : "translate-x-full"
        )}>
          <div className="flex items-center justify-between p-4 border-b lg:hidden">
            <h2 className="font-semibold">Story Bible</h2>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setRightSidebarOpen(false)}
            >
              <X className="h-5 w-5" />
            </Button>
          </div>
          <div className="flex-1 overflow-y-auto">
            {rightPane}
          </div>
        </div>
      </div>
    </div>
  )
}