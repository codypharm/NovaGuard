import { useState, useEffect } from "react"
import { User, AlertTriangle, Edit2, Search, X, Check } from "lucide-react" // Added Search
import { cn } from "@/lib/utils"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { createPatient, updatePatient, getPatientByMRN, type Patient } from "@/services/api"

interface PatientFormProps {
  initialPatient: Patient | null
  onSave: (patient: Patient) => void
  className?: string
}

export function PatientForm({ initialPatient, onSave, className }: PatientFormProps) {
  const [isEditing, setIsEditing] = useState(!initialPatient)
  const [isSaving, setIsSaving] = useState(false)
  const [isSearching, setIsSearching] = useState(false) // Added state
  
  const [formData, setFormData] = useState<Partial<Patient>>({
    name: "",
    date_of_birth: "",
    medical_record_number: "",
    weight: "",
    height: "",
    allergies: []
  })

  useEffect(() => {
    if (initialPatient) {
        setFormData(initialPatient)
        setIsEditing(false)
    }
  }, [initialPatient])

  const handleMRNSearch = async () => {
      if (!formData.medical_record_number) return
      setIsSearching(true)
      try {
          const patient = await getPatientByMRN(formData.medical_record_number)
          if (patient) {
              setFormData({
                  ...patient,
                  // Ensure allergies are mapped if necessary, assuming API returns correct shape
              })
              // Optional: Auto-switch to view mode? No, let user review.
          } else {
              // Not found
              console.log("Patient not found")
              // Could show a toast here
          }
      } catch (err) {
          console.error("Lookup failed", err)
      } finally {
          setIsSearching(false)
      }
  }

  const handleSave = async () => {
    if (!formData.name || !formData.date_of_birth) return 
    
    setIsSaving(true)
    try {
        const payload = {
            name: formData.name,
            date_of_birth: formData.date_of_birth,
            medical_record_number: formData.medical_record_number,
            weight: formData.weight,
            height: formData.height,
            egfr: formData.egfr ? Number(formData.egfr) : undefined,
            is_pregnant: formData.is_pregnant || false,
            is_nursing: formData.is_nursing || false,
            // Send allergies for sync (additions & deletions)
            allergies: formData.allergies?.map(a => ({
                patient_id: formData.id || 0, // Backend handles override/assignment
                allergen: a.allergen,
                allergy_type: "drug",
                severity: "severe" // Default for now, should refine UI to capture this
            }))
        }

        let savedPatient: Patient
        if (formData.id) {
            // Update Existing (PUT)
            savedPatient = await updatePatient(formData.id, payload)
        } else {
            // Create New (POST)
            savedPatient = await createPatient(payload)
        }

        setIsEditing(false)
        onSave(savedPatient)
    } catch (err) {
        console.error("Failed to save patient", err)
        alert("Failed to save patient. Check console.")
    } finally {
        setIsSaving(false)
    }
  }

  if (!isEditing && initialPatient) {
      // View Mode (Vertical Card)
      const age = new Date().getFullYear() - new Date(initialPatient.date_of_birth).getFullYear()
      return (
        <div className={cn("bg-white border rounded-xl p-4 shadow-sm relative group flex flex-col gap-4", className)}>
            <Button 
                variant="ghost" 
                size="icon" 
                className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={() => setIsEditing(true)}
            >
                <Edit2 className="h-4 w-4 text-slate-400" />
            </Button>

            <div className="flex flex-col items-center text-center pt-2">
                <div className="h-16 w-16 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 mb-3">
                    <User className="h-8 w-8" />
                </div>
                <div>
                    <h2 className="font-bold text-slate-900 text-lg">{initialPatient.name}</h2>
                    <p className="text-sm text-slate-500">MRN: {initialPatient.medical_record_number}</p>
                    <p className="text-xs font-mono bg-slate-100 px-2 py-1 rounded inline-block mt-1">
                        {age} years old
                        {initialPatient.is_pregnant && <span className="ml-2 text-pink-600 font-semibold">• Pregnant</span>}
                        {initialPatient.is_nursing && <span className="ml-2 text-teal-600 font-semibold">• Nursing</span>}
                        {initialPatient.egfr && <span className="ml-2 text-slate-600">• eGFR: {initialPatient.egfr}</span>}
                    </p>
                </div>
            </div>
            
            <div className="w-full h-px bg-slate-100"></div>

            <div className="w-full">
                <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle className="h-4 w-4 text-amber-500" />
                    <span className="text-sm font-semibold text-slate-700 uppercase tracking-wider">Allergies</span>
                </div>
                <div className="flex flex-wrap gap-2">
                    {initialPatient.allergies && initialPatient.allergies.length > 0 ? (
                        initialPatient.allergies.map((allergy, i) => (
                            <span key={i} className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-amber-50 text-amber-800 border border-amber-100">
                                {allergy.allergen}
                            </span>
                        ))
                    ) : (
                        <span className="text-sm text-slate-400 italic">No known allergies</span>
                    )}
                </div>
            </div>
        </div>
      )
  }

  // Edit Mode (Vertical Stack)
  return (
    <div className={cn("bg-white border rounded-xl p-4 shadow-sm space-y-4", className)}>
        <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                <User className="h-4 w-4 text-teal-600" />
                Patient Profile
            </h3>
            {initialPatient && (
                <Button variant="ghost" size="sm" onClick={() => setIsEditing(false)}>
                    Cancel
                </Button>
            )}
        </div>

        <div className="space-y-4">
        {/* MRN First */}
        <div className="space-y-2">
            <Label htmlFor="mrn">MRN (Medical Record Number)</Label>
            <div className="flex gap-2">
                <Input 
                    id="mrn" 
                    placeholder="Enter MRN to search..."
                    value={formData.medical_record_number || ""}
                    onChange={e => setFormData({...formData, medical_record_number: e.target.value})}
                    onKeyDown={e => e.key === 'Enter' && handleMRNSearch()}
                />
                <Button variant="outline" size="icon" onClick={handleMRNSearch} disabled={isSearching}>
                    {isSearching ? <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-500 border-t-transparent"/> : <Search className="h-4 w-4" />}
                </Button>
            </div>
            <p className="text-xs text-slate-500">Press Enter or Search to autofill existing patient.</p>
        </div>

        <div className="space-y-2">
            <Label htmlFor="name">Full Name</Label>
            <Input 
                id="name" 
                value={formData.name || ""}
                onChange={e => setFormData({...formData, name: e.target.value})}
            />
        </div>

        <div className="space-y-2">
            <Label htmlFor="dob">
                Date of Birth 
                {formData.date_of_birth && (
                    <span className="ml-2 text-xs text-slate-500 font-normal">
                        ({new Date().getFullYear() - new Date(formData.date_of_birth).getFullYear()} years old)
                    </span>
                )}
            </Label>
            <Input 
                id="dob" 
                type="date"
                value={formData.date_of_birth?.toString() || ""} 
                onChange={e => setFormData({...formData, date_of_birth: e.target.value})}
            />
        </div>

        {/* Vitals */}
        <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
                <Label htmlFor="weight">Weight</Label>
                <Input 
                    id="weight" 
                    placeholder="e.g. 70kg"
                    value={formData.weight || ""}
                    onChange={e => setFormData({...formData, weight: e.target.value})}
                />
            </div>
            <div className="space-y-2">
                <Label htmlFor="height">Height</Label>
                <Input 
                    id="height" 
                    placeholder="e.g. 175cm"
                    value={formData.height || ""}
                    onChange={e => setFormData({...formData, height: e.target.value})}
                />
            </div>
        </div>

        {/* Clinical Status */}
        <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
                <Label htmlFor="egfr">eGFR (mL/min)</Label>
                <Input 
                    id="egfr" 
                    type="number"
                    placeholder="e.g. 90"
                    value={formData.egfr || ""}
                    onChange={e => setFormData({...formData, egfr: e.target.value ? Number(e.target.value) : undefined})}
                />
            </div>
            
            <div className="flex flex-col justify-end space-y-3 pb-2">
                <div className="flex items-center space-x-2">
                    <input
                        type="checkbox"
                        id="is_pregnant"
                        checked={formData.is_pregnant || false}
                        onChange={e => setFormData({...formData, is_pregnant: e.target.checked})}
                        className="h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500"
                    />
                    <Label htmlFor="is_pregnant" className="font-normal cursor-pointer">Patient is Pregnant</Label>
                </div>
                <div className="flex items-center space-x-2">
                    <input
                        type="checkbox"
                        id="is_nursing"
                        checked={formData.is_nursing || false}
                        onChange={e => setFormData({...formData, is_nursing: e.target.checked})}
                        className="h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500"
                    />
                    <Label htmlFor="is_nursing" className="font-normal cursor-pointer">Patient is Nursing</Label>
                </div>
            </div>
        </div>

        {/* Allergies ... */}
        {/* Allergies (Tag Input) */}
        <div className="space-y-2">
            <Label>Allergies</Label>
            <div className="flex gap-2">
                <Input 
                    id="allergy-input"
                    placeholder="Type allergen (e.g. Penicillin) and press Enter"
                    onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                            e.preventDefault()
                            const val = e.currentTarget.value.trim()
                            if (val) {
                                const current = formData.allergies || []
                                if (!current.some(a => a.allergen.toLowerCase() === val.toLowerCase())) {
                                    setFormData({
                                        ...formData,
                                        allergies: [...current, { allergen: val, severity: "unknown" }]
                                    })
                                }
                                e.currentTarget.value = ""
                            }
                        }
                    }}
                />
                <Button 
                    variant="outline" 
                    onClick={() => {
                        const input = document.getElementById("allergy-input") as HTMLInputElement
                        const val = input.value.trim()
                        if (val) {
                            const current = formData.allergies || []
                            if (!current.some(a => a.allergen.toLowerCase() === val.toLowerCase())) {
                                setFormData({
                                    ...formData,
                                    allergies: [...current, { allergen: val, severity: "unknown" }]
                                })
                            }
                            input.value = ""
                        }
                    }}
                >
                    Add
                </Button>
            </div>
            
            <div className="flex flex-wrap gap-2 min-h-[40px] p-2 bg-slate-50 rounded-md border border-slate-100">
                {formData.allergies && formData.allergies.length > 0 ? (
                    formData.allergies.map((allergy, i) => (
                        <span key={i} className="inline-flex items-center px-2 py-1 rounded text-sm font-medium bg-amber-100 text-amber-800 border border-amber-200">
                            {allergy.allergen}
                            <button 
                                onClick={() => {
                                    const newList = formData.allergies?.filter((_, idx) => idx !== i)
                                    setFormData({...formData, allergies: newList})
                                }}
                                className="ml-1.5 hover:bg-amber-200 rounded-full p-0.5"
                            >
                                <X className="h-3 w-3" />
                            </button>
                        </span>
                    ))
                ) : (
                    <span className="text-sm text-slate-400 italic">No allergies added.</span>
                )}
            </div>
        </div>
        </div>

        <div className="flex justify-end pt-2">
            <Button 
                onClick={handleSave} 
                className="w-full bg-teal-600 hover:bg-teal-700" 
                disabled={isSaving || (!formData.name && !formData.medical_record_number)}
            >
                {isSaving ? (
                    <span className="flex items-center gap-2">
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></div>
                        Syncing...
                    </span>
                ) : (
                    <>
                        <Check className="h-4 w-4 mr-2" />
                        Sync Profile
                    </>
                )}
            </Button>
        </div>
    </div>
  )
}
