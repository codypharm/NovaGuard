import { useState, useEffect } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { getSessions, createSession as apiCreateSession, type Session } from '@/services/api'

export function useSession() {
  const [sessionId, setSessionId] = useState<string>("")
  const [sessionsHistory, setSessionsHistory] = useState<Session[]>([])
  const [loading, setLoading] = useState(false)

  // Fetch sessions history
  const refreshSessions = async () => {
      try {
          setLoading(true)
          const data = await getSessions()
          setSessionsHistory(data)
      } catch (err) {
          console.error("Failed to load sessions", err)
      } finally {
          setLoading(false)
      }
  }

  useEffect(() => {
    // 1. Load History
    refreshSessions()

    // 2. Check URL
    const params = new URLSearchParams(window.location.search)
    let id = params.get("session")

    // 3. Check LocalStorage if not in URL
    if (!id) {
        id = localStorage.getItem("nova_session_id")
    }

    // 4. Generate New if neither
    if (!id) {
        id = uuidv4()
    }

    // 5. Update State & Persistence
    if (id) {
        setSessionId(id)
        localStorage.setItem("nova_session_id", id)
        
        // Ensure session exists on backend
        apiCreateSession(id).catch(err => console.error("Failed to init session", err))
        
        // Update URL without reload if needed
        if (params.get("session") !== id) {
            const newUrl = new URL(window.location.href)
            newUrl.searchParams.set("session", id)
            window.history.replaceState({}, "", newUrl.toString())
        }
    }
  }, [])

  const createNewSession = async () => {
      const newId = uuidv4()
      setSessionId(newId)
      localStorage.setItem("nova_session_id", newId)
      
      const newUrl = new URL(window.location.href)
      newUrl.searchParams.set("session", newId)
      window.history.pushState({}, "", newUrl.toString())
      
      // Create on backend
      await apiCreateSession(newId)
      await refreshSessions() // Update list
      
      return newId
  }

  return { sessionId, sessionsHistory, loading, createNewSession, refreshSessions }
}
