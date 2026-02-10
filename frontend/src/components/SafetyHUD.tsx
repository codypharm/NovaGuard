import { useState } from 'react'
import { Header } from '@/components/Header'
import { DashboardLayout } from '@/components/DashboardLayout'
import { SafetyChat } from '@/components/SafetyChat'
import { PatientForm } from '@/components/PatientForm'
import { type Verdict } from '@/components/SafetyAnalysis'
import { processPrescription, type Patient } from '@/services/api'

export function SafetyHUD() {
  const [isProcessing, setIsProcessing] = useState(false)
  const [verdict, setVerdict] = useState<Verdict | null>(null)
  const [patient, setPatient] = useState<Patient | null>(null)
  
  // No automatic load
  /* 
  useEffect(() => {
    getPatient(1)
        .then(setPatient)
        .catch(err => console.error("Failed to load patient", err))
  }, []) 
  */

  const handleProcess = async (text: string, file: File | null) => {
    if (!file && !text) return
    
    // Auto-create guest if no patient (Simulated)
    let currentPatient = patient
    if (!currentPatient) {
        currentPatient = { id: 0, name: "Guest Patient", date_of_birth: new Date().toISOString(), medical_record_number: "GUEST", allergies: [] }
        setPatient(currentPatient)
    }
    
    setIsProcessing(true)
    setVerdict(null) 
    
    try {
        const result = await processPrescription(currentPatient.id, text, file)
        setVerdict(result.verdict as Verdict) 
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
            <SafetyChat verdict={verdict} isProcessing={isProcessing} onProcess={handleProcess} />
        </div>

        {/* SIDEBAR PROFILE (1 Col) */}
        <div className="lg:col-span-1 h-full overflow-y-auto">
            <PatientForm initialPatient={patient} onSave={setPatient} className="h-full" />
        </div>
      </div>
    </DashboardLayout>
  )
}
