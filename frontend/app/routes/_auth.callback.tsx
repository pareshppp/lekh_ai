import { useEffect } from 'react'
import { json, redirect, type LoaderFunctionArgs } from '@remix-run/node'
import { useNavigate, useSearchParams } from '@remix-run/react'
import { supabase } from '~/lib/supabase'

export async function loader({ request }: LoaderFunctionArgs) {
  const url = new URL(request.url)
  const code = url.searchParams.get('code')
  const error = url.searchParams.get('error')
  const errorDescription = url.searchParams.get('error_description')

  if (error) {
    console.error('Auth callback error:', error, errorDescription)
    // Redirect to login with error message
    return redirect('/login?error=' + encodeURIComponent(errorDescription || error))
  }

  if (code) {
    try {
      // Exchange the code for a session
      const { data, error: exchangeError } = await supabase.auth.exchangeCodeForSession(code)
      
      if (exchangeError) {
        console.error('Code exchange error:', exchangeError)
        return redirect('/login?error=' + encodeURIComponent(exchangeError.message))
      }

      if (data.session) {
        // Successful authentication, redirect to dashboard
        return redirect('/')
      }
    } catch (err) {
      console.error('Callback processing error:', err)
      return redirect('/login?error=Authentication failed')
    }
  }

  // No code or error, redirect to login
  return redirect('/login')
}

export default function AuthCallback() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  useEffect(() => {
    const handleAuthCallback = async () => {
      try {
        // Handle the auth callback
        const { data, error } = await supabase.auth.getSession()
        
        if (error) {
          console.error('Auth callback error:', error)
          navigate('/login?error=' + encodeURIComponent(error.message))
          return
        }

        if (data.session) {
          // User is authenticated, redirect to dashboard
          navigate('/')
        } else {
          // No session, redirect to login
          navigate('/login')
        }
      } catch (err) {
        console.error('Auth callback processing error:', err)
        navigate('/login?error=Authentication failed')
      }
    }

    handleAuthCallback()
  }, [navigate])

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center">
      <div className="text-center">
        <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
          Completing sign in...
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          Please wait while we complete your authentication.
        </p>
      </div>
    </div>
  )
}