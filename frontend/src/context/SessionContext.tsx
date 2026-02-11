import React, { createContext, useContext, useState, useEffect } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { getSessions, createSession as apiCreateSession, deleteSession as apiDeleteSession, type Session } from '@/services/api'

interface SessionContextType {
    sessionId: string
    sessionsHistory: Session[]
    loading: boolean
    createNewSession: () => Promise<string>
    refreshSessions: () => Promise<Session[]>
    switchSession: (id: string) => void
    deleteSession: (id: string) => Promise<void>
}

const SessionContext = createContext<SessionContextType | undefined>(undefined)

export function SessionProvider({ children }: { children: React.ReactNode }) {
    const [sessionId, setSessionId] = useState<string>("")
    const [sessionsHistory, setSessionsHistory] = useState<Session[]>([])
    const [loading, setLoading] = useState(false)

    // Initial Load
    useEffect(() => {
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
             // If the ID from localStorage isn't in the user's list, it might be stale or belong to another user.
             // We default to the most recent session, or create a new one.
             const isValid = id && sessions.some(s => s.id === id)
             
             if (!isValid) {
                 if (sessions.length > 0) {
                     // Switch to most recent
                     id = sessions[0].id
                 } else {
                     // No sessions exist, create new
                     id = uuidv4()
                 }
             }
             
             // Set state
             if (id) switchSession(id, false)
        }
        init()
    }, [])

    const refreshSessions = async () => {
        try {
            setLoading(true)
            const data = await getSessions()
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
        setSessionId(id)
        localStorage.setItem("nova_session_id", id)

        if (updateUrl) {
            const newUrl = new URL(window.location.href)
            newUrl.searchParams.set("session", id)
            window.history.pushState({}, "", newUrl.toString())
        }
        
        // Ensure backend knows about it (if new)
        // Optimization: checking specific format or if it's in history might save a call, 
        // but `apiCreateSession` is idempotent logic usually.
        apiCreateSession(id).catch(err => console.error("Session init warning", err))
    }

    const createNewSession = async () => {
        const newId = uuidv4()
        
        // Optimistic update
        const newSession: Session = {
            id: newId,
            title: "New Session",
            updated_at: new Date().toISOString()
        }
        
        setSessionsHistory(prev => [newSession, ...prev])
        switchSession(newId)
        
        try {
            await apiCreateSession(newId)
            await refreshSessions() // Get server truth
        } catch (err) {
            console.error("Failed to create session on server", err)
        }
        
        return newId
    }

    const deleteSession = async (id: string) => {
        try {
            // Optimistic update
            setSessionsHistory(prev => prev.filter(s => s.id !== id))
            
            // If deleting current session, switch to another
            if (sessionId === id) {
               const remaining = sessionsHistory.filter(s => s.id !== id)
               if (remaining.length > 0) {
                   switchSession(remaining[0].id)
               } else {
                   // Create new session if none left
                   await createNewSession()
               }
            }

            await apiDeleteSession(id)
        } catch (err) {
            console.error("Failed to delete session", err)
            // Revert on failure? Ideally yes, but for now simple log.
            await refreshSessions()
        }
    }

    return (
        <SessionContext.Provider value={{
            sessionId,
            sessionsHistory,
            loading,
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
