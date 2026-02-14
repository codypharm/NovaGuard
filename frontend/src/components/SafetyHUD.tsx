import { useState, useEffect } from 'react'
import { Header } from '@/components/Header'
import { DashboardLayout } from '@/components/DashboardLayout'
import { SafetyChat } from '@/components/SafetyChat'
import { PatientForm } from '@/components/PatientForm'
import { type Verdict } from '@/components/SafetyAnalysis'
import { streamClinicalInteraction, type Patient } from '@/services/api'
import { useSessionContext } from "@/context/SessionContext"
import DrugOperationsModule from '@/components/DrugOperationsModule'
import PatientDatabaseModule from '@/components/PatientDatabaseModule'

export function SafetyHUD() {
  const { sessionId, sessionsHistory, refreshSessions, activeModule } = useSessionContext()
  const [isProcessing, setIsProcessing] = useState(false)
  const [processingStep, setProcessingStep] = useState<string | null>(null)
  const [verdict, setVerdict] = useState<Verdict | null>(null)
  const [patient, setPatient] = useState<Patient | null>(null)
  const [assistantResponse, setAssistantResponse] = useState<string | null>(null)

  // Sync patient data when session changes
  useEffect(() => {
    if (!sessionId) return
    
    // Find active session in history
    const activeSession = sessionsHistory.find(s => s.id === sessionId)
    
    // If it has patient data, load it. Otherwise clear.
    if (activeSession?.patient) {
        console.log("Loading patient for session:", activeSession.patient.name)
        setPatient(activeSession.patient)
    } else {
        setPatient(null)
    }
  }, [sessionId, sessionsHistory])

  const handleProcess = async (text: string, file: File | null) => {
    if (!sessionId) return
    if (!file && !text) return
    
    setIsProcessing(true)
    setProcessingStep(null)
    setVerdict(null) 
    
    try {
        await streamClinicalInteraction(
            sessionId,
            patient ? patient.id : null,
            text,
            file,
            {
                onProgress: (event) => {
                    setProcessingStep(event.label)
                },
                onComplete: (event) => {
                    if (event.verdict) {
                        setVerdict(event.verdict as Verdict)
                    }
                    if (event.assistant_response) {
                        setAssistantResponse(event.assistant_response)
                    }
                },
                onError: (event) => {
                    setAssistantResponse(
                        `**⚠️ ${event.message}**\n\nPlease try again or rephrase your query.`
                    )
                },
            }
        )
        
        // Refresh session list to show updated title
        refreshSessions()

    } catch (err) {
        console.error("Analysis Failed", err)
        setAssistantResponse(
            "**⚠️ Connection Error**\n\nCould not reach the server. Please check your connection and try again."
        )
    } finally {
        setIsProcessing(false)
        setProcessingStep(null)
    }
  }

  // ALWAYS RETURN SIDEBAR LAYOUT
  return (
    <DashboardLayout>
      <div className="flex items-center justify-between mb-8">
         <h1 className="text-2xl font-bold tracking-tight text-slate-900 truncate mr-4">
            {activeModule === 'drug-operations' 
                ? "Drug Operations Center" 
                : activeModule === 'patient-database'
                ? "Patient Database & Profiles"
                : (patient ? `Safety Check - ${patient.name}` : "New Safety Check")
            }
         </h1>
         <div className="flex-shrink-0">
            <Header /> 
         </div>
      </div>

      {activeModule === 'drug-operations' ? (
        <div className="h-[calc(100vh-9rem)] overflow-y-auto">
            <DrugOperationsModule />
        </div>
      ) : activeModule === 'patient-database' ? (
        <div className="h-[calc(100vh-9rem)] overflow-y-auto">
            <PatientDatabaseModule />
        </div>
      ) : (
        <div className="h-[calc(100vh-9rem)] grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* MAIN CHAT AREA (3 Cols) */}
            <div className="lg:col-span-3 h-full overflow-hidden">
                <SafetyChat 
                    sessionId={sessionId}
                    verdict={verdict} 
                    isProcessing={isProcessing}
                    processingStep={processingStep}
                    onProcess={handleProcess} 
                    assistantResponse={assistantResponse}
                    onResponseShown={() => setAssistantResponse(null)}
                />
            </div>

            {/* SIDEBAR PROFILE (1 Col) */}
            <div className="lg:col-span-1 h-full overflow-y-auto">
                <PatientForm 
                    key={patient ? patient.id : 'new'} 
                    initialPatient={patient} 
                    onSave={setPatient} 
                    className="h-full" 
                />
            </div>
        </div>
      )}
    </DashboardLayout>
  )
}
