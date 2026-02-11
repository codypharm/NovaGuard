import { useState } from 'react'
import { Header } from '@/components/Header'
import { DashboardLayout } from '@/components/DashboardLayout'
import { SafetyChat } from '@/components/SafetyChat'
import { PatientForm } from '@/components/PatientForm'
import { type Verdict } from '@/components/SafetyAnalysis'
import { processClinicalInteraction, type Patient } from '@/services/api'
import { useSession } from '@/hooks/useSession'

export function SafetyHUD() {
  const { sessionId } = useSession()
  const [isProcessing, setIsProcessing] = useState(false)
  const [verdict, setVerdict] = useState<Verdict | null>(null)
  const [patient, setPatient] = useState<Patient | null>(null)
  const [assistantResponse, setAssistantResponse] = useState<string | null>(null)
  
  const handleProcess = async (text: string, file: File | null) => {
    if (!sessionId) return // Should be ready by mount
    if (!file && !text) return
    
    setIsProcessing(true)
    setVerdict(null) 
    
    try {
        // Pass sessionId (always) and patientId (if synced)
        const result = await processClinicalInteraction(
            sessionId, 
            patient ? patient.id : null, 
            text, 
            file
        )
        
        // Handle Assistant Response & Verdict
        if (result.verdict) {
            setVerdict(result.verdict as Verdict)
        }

        if (result.assistant_response) {
            setAssistantResponse(result.assistant_response)
        }
        
        // Handle External Actions (e.g., Open Source)
        if (result.external_url) {
            window.open(result.external_url, '_blank')
        }

    } catch (err) {
        console.error("Analysis Failed", err)
    } finally {
        setIsProcessing(false)
    }
  }

  // ALWAYS RETURN SIDEBAR LAYOUT
  return (
    <DashboardLayout>
      <div className="flex items-center justify-between mb-8">
         <h1 className="text-2xl font-bold tracking-tight text-slate-900 truncate mr-4">
            {patient ? `Safety Check - ${patient.name}` : "New Safety Check"}
         </h1>
         <div className="flex-shrink-0">
            <Header /> 
         </div>
      </div>

      <div className="h-[calc(100vh-9rem)] grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* MAIN CHAT AREA (3 Cols) */}
        <div className="lg:col-span-3 h-full overflow-hidden">
            <SafetyChat 
                sessionId={sessionId}
                verdict={verdict} 
                isProcessing={isProcessing} 
                onProcess={handleProcess} 
                assistantResponse={assistantResponse}
                onResponseShown={() => setAssistantResponse(null)}
            />
        </div>

        {/* SIDEBAR PROFILE (1 Col) */}
        <div className="lg:col-span-1 h-full overflow-y-auto">
            <PatientForm initialPatient={patient} onSave={setPatient} className="h-full" />
        </div>
      </div>
    </DashboardLayout>
  )
}
