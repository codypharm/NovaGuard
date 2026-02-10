import { User, AlertTriangle } from "lucide-react"
import type { Patient } from "@/services/api"

interface PatientHeaderProps {
  patient: Patient | null
  isLoading: boolean
}

export function PatientHeader({ patient, isLoading }: PatientHeaderProps) {
  if (isLoading) return <div className="h-16 animate-pulse bg-slate-100 rounded-lg mb-6"></div>
  
  if (!patient) return null

  // Calculate Age (Rough approx)
  const age = new Date().getFullYear() - new Date(patient.date_of_birth).getFullYear()

  return (
    <div className="bg-white border rounded-xl p-4 mb-6 shadow-sm flex flex-wrap gap-6 items-center">
        {/* Identity */}
        <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-500">
                <User className="h-5 w-5" />
            </div>
            <div>
                <h2 className="font-bold text-slate-900">{patient.name}</h2>
                <p className="text-xs text-slate-500">MRN: {patient.medical_record_number} • {age} years</p>
            </div>
        </div>

        {/* Divider */}
        <div className="h-8 w-px bg-slate-200 hidden md:block"></div>

        {/* Allergies */}
        <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
                <AlertTriangle className="h-3 w-3 text-amber-500" />
                <span className="text-xs font-semibold text-slate-700 uppercase tracking-wider">Allergies</span>
            </div>
            <div className="flex flex-wrap gap-2">
                {patient.allergies && patient.allergies.length > 0 ? (
                    patient.allergies.map((allergy, i) => (
                        <span key={i} className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-800 border border-amber-100">
                            {allergy.allergen}
                        </span>
                    ))
                ) : (
                    <span className="text-xs text-slate-400 italic">No known allergies</span>
                )}
            </div>
        </div>
    </div>
  )
}
