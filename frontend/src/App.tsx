import { SafetyHUD } from "@/components/SafetyHUD"
import { SessionProvider } from "@/context/SessionContext"
import { Toaster } from "@/components/ui/sonner"
import { ClerkProvider, SignedIn, SignedOut, useAuth } from "@clerk/clerk-react"
import LoginPage from "@/pages/LoginPage"
import { setTokenProvider } from "@/services/api"
import { useEffect } from "react"

// Get key from environment
const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

if (!PUBLISHABLE_KEY) {
  throw new Error("Missing Publishable Key")
}

function TokenSync({ children }: { children: React.ReactNode }) {
  const { getToken } = useAuth()
  
  useEffect(() => {
    setTokenProvider(getToken)
  }, [getToken])

  return <>{children}</>
}

function App() {
  return (
    <ClerkProvider 
      publishableKey={PUBLISHABLE_KEY}
      appearance={{
        variables: {
          colorPrimary: '#10b981', // emerald-500 (Safety Green)
          fontSize: '16px',
        },
        layout: {
          socialButtonsPlacement: 'bottom',
          socialButtonsVariant: 'iconButton',
        }
      }}
    >
      <SignedIn>
        <TokenSync>
            <SessionProvider>
            <SafetyHUD />
            <Toaster />
            </SessionProvider>
        </TokenSync>
      </SignedIn>
      <SignedOut>
        <LoginPage />
      </SignedOut>
    </ClerkProvider>
  )
}

export default App
