import { SafetyHUD } from "@/components/SafetyHUD"
import { SessionProvider } from "@/context/SessionContext"

import { Toaster } from "@/components/ui/sonner"

function App() {
  return (
    <SessionProvider>
      <SafetyHUD />
      <Toaster />
    </SessionProvider>
  )
}

export default App
