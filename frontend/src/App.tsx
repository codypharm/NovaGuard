import { SafetyHUD } from "@/components/SafetyHUD"
import { SessionProvider } from "@/context/SessionContext"

function App() {
  return (
    <SessionProvider>
      <SafetyHUD />
    </SessionProvider>
  )
}

export default App
