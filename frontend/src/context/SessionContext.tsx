import React, { createContext, useContext, useState, useEffect } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { getSessions, createSession as apiCreateSession, deleteSession as apiDeleteSession, type Session, setTokenProvider } from '@/services/api'
import { useAuth } from '@clerk/clerk-react'

interface SessionContextType {
    sessionId: string
    sessionsHistory: Session[]
    loading: boolean
    activeModule: 'safety-check' | 'drug-operations' | 'patient-database'
    setActiveModule: (module: 'safety-check' | 'drug-operations' | 'patient-database') => void
    createNewSession: (patientId?: number) => Promise<string>
    refreshSessions: () => Promise<Session[]>
    switchSession: (id: string) => void
    deleteSession: (id: string) => Promise<void>
}

const SessionContext = createContext<SessionContextType | undefined>(undefined)

export function SessionProvider({ children }: { children: React.ReactNode }) {
    const [sessionId, setSessionId] = useState<string>("")
    const [sessionsHistory, setSessionsHistory] = useState<Session[]>([])
    const [activeModule, setActiveModule] = useState<'safety-check' | 'drug-operations' | 'patient-database'>('safety-check')
    const [loading, setLoading] = useState(false)

    const { isLoaded, userId, getToken } = useAuth()
    const initialized = React.useRef(false)

    // Initial Load
    useEffect(() => {
        if (!isLoaded || !userId) return
        
        // Ensure the token provider in api.ts is set before we fetch
        // (Double safety, though TokenSync in App.tsx should handle it)
        setTokenProvider(getToken)

        if (initialized.current) return
        initialized.current = true

        const init = async () => {
             const sessions = await refreshSessions() || []
             
             // Check URL first
             const params = new URLSearchParams(window.location.search)
             let id = params.get("session")
             
             // Check LocalStorage if no URL param
             if (!id) {
                 id = localStorage.getItem("nova_session_id")
             }

             // Validate ID against user's session list
             let shouldCreate = false
             const isValid = id && sessions.some(s => s.id === id)
             
             if (!isValid) {
                 if (sessions.length > 0) {
                     // Switch to most recent
                     id = sessions[0].id
                 } else {
                     // No sessions exist, create new
                     id = uuidv4()
                     shouldCreate = true
                 }
             }
             
             // Set state
             if (id) {
                 switchSession(id, false)
                 if (shouldCreate) {
                     apiCreateSession(id).catch(err => console.error("Session init creation failed", err))
                 }
             }
        }
        init()
    }, [isLoaded, userId, getToken])

    const refreshSessions = async () => {
        try {
            setLoading(true)
            // console.log("📥 SessionContext: refreshSessions called")
            const data = await getSessions()
            // console.log("📥 SessionContext: getSessions returned", data.length, "sessions", data)
            setSessionsHistory(data)
            return data
        } catch (err) {
            console.error("Failed to load sessions", err)
            return []
        } finally {
            setLoading(false)
        }
    }

    const switchSession = (id: string, updateUrl = true) => {
       // console.log(`🔄 SessionContext: switchSession to ${id} (updateUrl: ${updateUrl})`)
        setSessionId(id)
        localStorage.setItem("nova_session_id", id)

        if (updateUrl) {
            const newUrl = new URL(window.location.href)
            newUrl.searchParams.set("session", id)
            window.history.pushState({}, "", newUrl.toString())
        }
    }

    const isCreatingRef = React.useRef(false)

    const createNewSession = async (patientId?: number) => {
        if (isCreatingRef.current) {
            // console.warn("⚠️ createNewSession blocked: already in progress")
            return ""
        }
        isCreatingRef.current = true
        // console.log("✨ SessionContext: createNewSession START")
        
        const newId = uuidv4()
        
        try {
            console.log("📡 API: Calling apiCreateSession", newId, patientId)
            await apiCreateSession(newId, patientId)
            
            // Switch session first to ensure UI feels responsive
            switchSession(newId)
            
            // Wait slightly before refreshing to ensure DB consistency
            // (Postgres commit latency might be >0ms if under load)
            // await new Promise(r => setTimeout(r, 100))
            
            // Fetch updated list from server
            const updatedSessions = await refreshSessions()
            
            // Verify if the session was actually added (server-side consistency)
            if (!updatedSessions.some(s => s.id === newId)) {
                console.warn("⚠️ Session created but not returned by list API yet")
                // Manually append only if server didn't return it yet (rare race)
                setSessionsHistory(prev => [
                    { id: newId, title: "New Session", updated_at: new Date().toISOString() }, 
                    ...prev
                ])
            }
        } catch (err) {
            console.error("Failed to create session on server", err)
        } finally {
            isCreatingRef.current = false
        }
        
        return newId
    }

    const deleteSession = async (id: string) => {
        try {
            // 1. Delete on server first to ensure consistency
            await apiDeleteSession(id)

            // 2. Filter local state
            const remaining = sessionsHistory.filter(s => s.id !== id)
            setSessionsHistory(remaining)
            
            // 3. Handle active session switch
            if (sessionId === id) {
               if (remaining.length > 0) {
                   switchSession(remaining[0].id)
               } else {
                   // No sessions left -> Create new one
                   // Since delete is done, createNewSession -> refreshSessions will be clean
                   await createNewSession()
               }
            } else {
                // Just refresh to be sure
                await refreshSessions()
            }

        } catch (err) {
            console.error("Failed to delete session", err)
            await refreshSessions()
        }
    }

    return (
        <SessionContext.Provider value={{
            sessionId,
            sessionsHistory,
            loading,
            activeModule,
            setActiveModule,
            createNewSession,
            refreshSessions,
            switchSession,
            deleteSession
        }}>
            {children}
        </SessionContext.Provider>
    )
}

export function useSessionContext() {
    const context = useContext(SessionContext)
    if (context === undefined) {
        throw new Error("useSessionContext must be used within a SessionProvider")
    }
    return context
}
