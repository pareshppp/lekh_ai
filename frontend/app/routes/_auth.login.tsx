import { useEffect } from 'react'
import { json, redirect, type LoaderFunctionArgs, type MetaFunction } from '@remix-run/node'
import { useLoaderData, useNavigate } from '@remix-run/react'
import { Auth } from '@supabase/auth-ui-react'
import { ThemeSupa } from '@supabase/auth-ui-shared'
import { supabase } from '~/lib/supabase'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~/components/ui/card'

export const meta: MetaFunction = () => {
  return [
    { title: "Login | Lekh AI" },
    { name: "description", content: "Sign in to Lekh AI to start creating stories with AI" },
  ]
}

export async function loader({ request }: LoaderFunctionArgs) {
  // Get the current session from Supabase
  const { data: { session } } = await supabase.auth.getSession()
  
  // If user is already logged in, redirect to dashboard
  if (session) {
    return redirect('/')
  }

  return json({ 
    supabaseUrl: process.env.VITE_SUPABASE_URL!,
    supabaseAnonKey: process.env.VITE_SUPABASE_ANON_KEY!
  })
}

export default function Login() {
  const { supabaseUrl, supabaseAnonKey } = useLoaderData<typeof loader>()
  const navigate = useNavigate()

  useEffect(() => {
    // Listen for auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_IN' && session) {
        navigate('/')
      }
    })

    return () => subscription.unsubscribe()
  }, [navigate])

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
            Lekh AI
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Collaborative Story Creation with AI
          </p>
        </div>

        <Card>
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl font-bold text-center">Welcome back</CardTitle>
            <CardDescription className="text-center">
              Sign in to your account to continue creating amazing stories
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Auth
              supabaseClient={supabase}
              appearance={{ 
                theme: ThemeSupa,
                style: {
                  button: { 
                    background: 'rgb(59 130 246)', 
                    color: 'white',
                    borderRadius: '6px',
                  },
                  anchor: { 
                    color: 'rgb(59 130 246)',
                  },
                }
              }}
              providers={['google', 'github']}
              redirectTo={typeof window !== 'undefined' ? `${window.location.origin}/auth/callback` : '/auth/callback'}
              onlyThirdPartyProviders={false}
              magicLink={true}
              showLinks={true}
              theme="light"
            />
          </CardContent>
        </Card>

        <div className="mt-8 text-center text-sm text-gray-600 dark:text-gray-400">
          <p>
            By signing in, you agree to our{' '}
            <a href="#" className="text-blue-600 hover:underline">Terms of Service</a>{' '}
            and{' '}
            <a href="#" className="text-blue-600 hover:underline">Privacy Policy</a>
          </p>
        </div>
      </div>
    </div>
  )
}