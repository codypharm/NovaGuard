import { useState, useEffect } from "react"
import { User, AlertTriangle, Edit2, Search, X, Check, Activity, Dna, Camera, Trash2, ChevronDown, ChevronRight, Pill } from "lucide-react"
import { toast } from "sonner"
import { cn } from "@/lib/utils"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { createPatient, updatePatient, getPatientByMRN, scanLabResults, deleteLabResult, type Patient } from "@/services/api"

interface PatientFormProps {
  initialPatient: Patient | null
  onSave: (patient: Patient) => void
  className?: string
}

export function PatientForm({ initialPatient, onSave, className }: PatientFormProps) {
  const [isEditing, setIsEditing] = useState(!initialPatient)
  const [isSaving, setIsSaving] = useState(false)
  const [isSearching, setIsSearching] = useState(false) // Added state
  const [isDragging, setIsDragging] = useState(false)
  
  const [formData, setFormData] = useState<Partial<Patient>>({
    name: "",
    date_of_birth: "",
    medical_record_number: "",
    weight: "",
    height: "",
    allergies: [],
    genetic_markers: [],
    lab_results: []
  })
  
  const [isScanningLab, setIsScanningLab] = useState(false)
  const [expandedLabDates, setExpandedLabDates] = useState<Record<string, boolean>>({})

  const toggleLabDate = (date: string) => {
      setExpandedLabDates(prev => ({...prev, [date]: !prev[date]}))
  }

  const [expandedDrugDates, setExpandedDrugDates] = useState<Record<string, boolean>>({})
  const toggleDrugDate = (date: string) => {
      setExpandedDrugDates(prev => ({...prev, [date]: !prev[date]}))
  }

  useEffect(() => {
    if (initialPatient) {
        setFormData(initialPatient)
        setIsEditing(false)
    } else {
        setIsEditing(true)
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
              })
              toast.success("Patient profile loaded")
          } else {
              toast.error("Patient not found with that MRN")
          }
      } catch (err) {
          console.error("Lookup failed", err)
          toast.error("Failed to search for patient")
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
            allergies: formData.allergies?.map(a => ({
                allergen: a.allergen,
                allergy_type: "drug",
                severity: "severe"
            })),
            genetic_markers: formData.genetic_markers?.map(g => ({
                gene: g.gene,
                phenotype: g.phenotype,
                source: g.source || "Manual"
            })),
            lab_results: formData.lab_results?.map(l => ({
                test_name: l.test_name,
                value: l.value,
                unit: l.unit,
                reference_range: l.reference_range,
                is_abnormal: l.is_abnormal,
                source: l.source || "vision",
                collected_at: l.collected_at
            })) as any
        }

        let savedPatient: Patient
        if (formData.id) {
            savedPatient = await updatePatient(formData.id, payload)
        } else {
            savedPatient = await createPatient(payload)
        }

        setIsEditing(false)
        onSave(savedPatient)
        toast.success("Profile synced successfully")
    } catch (err) {
        console.error("Failed to save patient", err)
        toast.error("Failed to save patient profile")
    } finally {
        setIsSaving(false)
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setIsDragging(false)
  }

  const handleDrop = async (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setIsDragging(false)

      const file = e.dataTransfer.files?.[0]
      if (!file) return

      setIsScanningLab(true)
      toast.info("Scanning lab report from drop...")
      try {
          const newLabs = await scanLabResults(file)
          toast.success(`Successfully extracted ${newLabs.length} biomarkers!`)
          
          if (!isEditing && initialPatient) {
              onSave({...initialPatient, lab_results: [...(initialPatient.lab_results || []), ...newLabs]})
          } else {
              setFormData(prev => ({
                  ...prev,
                  lab_results: [...(prev.lab_results || []), ...newLabs]
              }))
          }
      } catch (err) {
          console.error(err)
          toast.error("Failed to scan labs from drop")
      } finally {
          setIsScanningLab(false)
      }
  }

  // View Mode
  if (!isEditing && initialPatient) {
      const age = initialPatient.date_of_birth ? new Date().getFullYear() - new Date(initialPatient.date_of_birth).getFullYear() : 'N/A'
      
      return (
        <div 
            className={cn(
                "bg-white border rounded-xl p-4 shadow-sm w-full relative group flex flex-col gap-4 transition-colors duration-200", 
                isDragging ? "border-teal-500 border-dashed bg-teal-50/30" : "",
                className
            )}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
        >
            {isDragging && (
                <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-teal-50/90 rounded-xl backdrop-blur-[1px] border-2 border-teal-500 border-dashed pointer-events-none">
                    <Activity className="h-10 w-10 text-teal-600 mb-2 animate-pulse" />
                    <p className="text-teal-700 font-semibold text-lg">Drop lab report to scan</p>
                </div>
            )}
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
                
                
                {/* GENETICS (PGx) VIEW */}
                <div className="flex items-center gap-2 mt-5 mb-2">
                    <Dna className="h-4 w-4 text-purple-500" />
                    <span className="text-sm font-semibold text-slate-700 uppercase tracking-wider">Genetics (PGx)</span>
                </div>
                <div className="flex flex-wrap gap-2">
                    {initialPatient.genetic_markers && initialPatient.genetic_markers.length > 0 ? (
                        initialPatient.genetic_markers.map((marker, i) => (
                            <span key={i} className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-purple-50 text-purple-800 border border-purple-100">
                                {marker.gene}: {marker.phenotype}
                            </span>
                        ))
                    ) : (
                        <span className="text-sm text-slate-400 italic">No genetic markers tracked</span>
                    )}
                </div>

                {/* MEDICAL HISTORY (DRUGS) VIEW */}
                <div className="flex items-center gap-2 mt-5 mb-2">
                    <Pill className="h-4 w-4 text-emerald-500" />
                    <span className="text-sm font-semibold text-slate-700 uppercase tracking-wider">Medical History</span>
                </div>
                <div className="flex flex-col gap-3">
                    {initialPatient.drug_history && initialPatient.drug_history.length > 0 ? (
                        Object.entries(
                            initialPatient.drug_history.reduce((acc: Record<string, any[]>, drug: any) => {
                                const date = drug.start_date ? new Date(drug.start_date).toLocaleDateString() : 'Unknown Date';
                                if (!acc[date]) acc[date] = [];
                                acc[date].push(drug);
                                return acc;
                            }, {})
                        ).sort((a, b) => {
                            if (a[0] === 'Unknown Date') return 1;
                            if (b[0] === 'Unknown Date') return -1;
                            return new Date(b[0]).getTime() - new Date(a[0]).getTime();
                        }).map(([date, drugs]: [string, any]) => (
                            <div key={date} className="bg-white border rounded shadow-sm overflow-hidden">
                                <button 
                                    onClick={() => toggleDrugDate(date)}
                                    className="w-full flex items-center justify-between px-3 py-2 bg-slate-50 hover:bg-slate-100 transition-colors"
                                >
                                    <span className="text-xs font-semibold text-slate-700">{date} ({drugs.length} drugs)</span>
                                    {expandedDrugDates[date] ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
                                </button>
                                {expandedDrugDates[date] && (
                                    <div className="p-2 flex flex-col gap-1 border-t">
                                        {drugs.map((drug: any, i: number) => (
                                            <div key={i} className="text-xs bg-slate-50/50 p-1.5 rounded flex justify-between items-center">
                                                <div className="flex flex-col">
                                                    <span className="font-medium text-slate-700">{drug.drug_name}</span>
                                                    {(drug.dose || drug.frequency) && (
                                                        <span className="text-[10px] text-slate-500">{drug.dose !== 'Unknown' ? drug.dose : ''} {drug.dose !== 'Unknown' && drug.frequency !== 'Unknown' ? '•' : ''} {drug.frequency !== 'Unknown' ? drug.frequency : ''}</span>
                                                    )}
                                                </div>
                                                <div className="text-right">
                                                    <span className={drug.is_active ? "text-emerald-600 font-semibold" : "text-slate-400 font-semibold"}>
                                                        {drug.is_active ? "Active" : "Discontinued"}
                                                    </span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        ))
                    ) : (
                        <span className="text-sm text-slate-400 italic">No drug history recorded</span>
                    )}
                </div>

                {/* LAB RESULTS VIEW */}
                <div className="flex items-center gap-2 mt-5 mb-2">
                    <Activity className="h-4 w-4 text-blue-500" />
                    <span className="text-sm font-semibold text-slate-700 uppercase tracking-wider">Lab Results</span>
                </div>
                <div className="flex flex-col gap-3">
                    {initialPatient.lab_results && initialPatient.lab_results.length > 0 ? (
                        Object.entries(
                            initialPatient.lab_results.reduce((acc: Record<string, any[]>, lab: any) => {
                                const date = lab.collected_at ? new Date(lab.collected_at).toLocaleDateString() : 'Unknown Date';
                                if (!acc[date]) acc[date] = [];
                                acc[date].push(lab);
                                return acc;
                            }, {})
                        ).map(([date, labs]: [string, any]) => (
                            <div key={date} className="bg-white border rounded shadow-sm overflow-hidden">
                                <button 
                                    onClick={() => toggleLabDate(date)}
                                    className="w-full flex items-center justify-between px-3 py-2 bg-slate-50 hover:bg-slate-100 transition-colors"
                                >
                                    <span className="text-xs font-semibold text-slate-700">{date} ({labs.length} tests)</span>
                                    {expandedLabDates[date] ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
                                </button>
                                {expandedLabDates[date] && (
                                    <div className="p-2 flex flex-col gap-1 border-t">
                                        {labs.map((lab: any, i: number) => (
                                            <div key={i} className="text-xs bg-slate-50/50 p-1.5 rounded flex justify-between items-center">
                                                <div className="flex flex-col">
                                                    <span className="font-medium text-slate-700">{lab.test_name}</span>
                                                </div>
                                                <div className="text-right">
                                                    <span className={lab.is_abnormal ? "text-red-600 font-bold" : "text-emerald-600 font-semibold"}>
                                                        {lab.value} {lab.unit}
                                                    </span>
                                                    <div className="text-[10px] text-slate-400">Range: {lab.reference_range}</div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        ))
                    ) : (
                        <span className="text-sm text-slate-400 italic">No lab results on file</span>
                    )}
                </div>



                {/* LAB UPLOAD (always visible in view mode) */}
                <div className="mt-5 pt-4 border-t border-slate-100">
                    <div className="flex items-center gap-2 mb-3">
                        <Camera className="h-4 w-4 text-blue-500" />
                        <span className="text-sm font-semibold text-slate-700 uppercase tracking-wider">Upload Lab Report</span>
                    </div>
                    <div className="flex flex-col sm:flex-row gap-2 items-start sm:items-center bg-teal-50/50 p-3 rounded-md border border-teal-100">
                        <input type="file" id="lab-image-view" accept="image/*" className="w-full text-xs flex-1 file:mr-3 file:py-1 file:px-3 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-teal-100 file:text-teal-700 hover:file:bg-teal-200" />
                        <Button 
                            type="button"
                            size="sm" 
                            variant="secondary" 
                            className="w-full sm:w-auto bg-white shrink-0"
                            disabled={isScanningLab}
                            onClick={async () => {
                                const input = document.getElementById("lab-image-view") as HTMLInputElement
                                const file = input.files?.[0]
                                if (!file) return toast.error("Select an image first")
                                
                                setIsScanningLab(true)
                                toast.info("Scanning lab report...")
                                try {
                                    const newLabs = await scanLabResults(file)
                                    toast.success(`Successfully extracted ${newLabs.length} biomarkers!`)
                                    input.value = ''
                                    // Trigger parent refresh
                                    onSave({...initialPatient, lab_results: [...(initialPatient.lab_results || []), ...newLabs]})
                                } catch (e) {
                                    toast.error("Failed to scan labs")
                                } finally {
                                    setIsScanningLab(false)
                                }
                            }}
                        >
                            {isScanningLab ? "Scanning..." : <><Camera className="h-4 w-4 mr-1" /> Scan</>}
                        </Button>
                    </div>
                </div>
            </div>
        </div>
      )
  }

  // Edit Mode (Vertical Stack)
  return (
    <div 
        className={cn(
            "bg-white border rounded-xl p-4 shadow-sm space-y-4 relative transition-colors duration-200", 
            isDragging ? "border-teal-500 border-dashed bg-teal-50/30" : "",
            className
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
    >
        {isDragging && (
            <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-teal-50/90 rounded-xl backdrop-blur-[1px] border-2 border-teal-500 border-dashed pointer-events-none">
                <Activity className="h-10 w-10 text-teal-600 mb-2 animate-pulse" />
                <p className="text-teal-700 font-semibold text-lg">Drop lab report to scan</p>
            </div>
        )}
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

        {/* Genetics (PGx) */}
        <div className="space-y-2">
            <Label className="flex items-center gap-2 text-purple-700"><Dna className="h-4 w-4" /> Genetics (PGx)</Label>
            <div className="flex gap-2">
                <Input 
                    id="gene-input"
                    placeholder="Gene (e.g. CYP2C19)"
                    className="w-1/3"
                />
                <Input 
                    id="phenotype-input"
                    placeholder="Phenotype (e.g. Poor Metabolizer)"
                    className="flex-1"
                    onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                            e.preventDefault()
                            const geneInput = document.getElementById("gene-input") as HTMLInputElement
                            const phenotypeInput = document.getElementById("phenotype-input") as HTMLInputElement
                            const gene = geneInput.value.trim()
                            const phenotype = phenotypeInput.value.trim()
                            
                            if (gene && phenotype) {
                                const current = formData.genetic_markers || []
                                if (!current.some(g => g.gene.toLowerCase() === gene.toLowerCase())) {
                                    setFormData({
                                        ...formData,
                                        genetic_markers: [...current, { id: Date.now(), gene, phenotype, source: "Manual" }]
                                    })
                                }
                                geneInput.value = ""
                                phenotypeInput.value = ""
                                geneInput.focus()
                            }
                        }
                    }}
                />
                <Button 
                    variant="outline" 
                    onClick={() => {
                        const geneInput = document.getElementById("gene-input") as HTMLInputElement
                        const phenotypeInput = document.getElementById("phenotype-input") as HTMLInputElement
                        const gene = geneInput.value.trim()
                        const phenotype = phenotypeInput.value.trim()
                        
                        if (gene && phenotype) {
                            const current = formData.genetic_markers || []
                            if (!current.some(g => g.gene.toLowerCase() === gene.toLowerCase())) {
                                setFormData({
                                    ...formData,
                                    genetic_markers: [...current, { id: Date.now(), gene, phenotype, source: "Manual" }]
                                })
                            }
                            geneInput.value = ""
                            phenotypeInput.value = ""
                        }
                    }}
                >
                    Add
                </Button>
            </div>
            
            <div className="flex flex-wrap gap-2 min-h-[40px] p-2 bg-slate-50 rounded-md border border-slate-100">
                {formData.genetic_markers && formData.genetic_markers.length > 0 ? (
                    formData.genetic_markers.map((marker, i) => (
                        <span key={i} className="inline-flex items-center px-2 py-1 rounded text-sm font-medium bg-purple-100 text-purple-800 border border-purple-200">
                            <span className="font-bold mr-1">{marker.gene}:</span> {marker.phenotype}
                            <button 
                                onClick={() => {
                                    const newList = formData.genetic_markers?.filter((_, idx) => idx !== i)
                                    setFormData({...formData, genetic_markers: newList})
                                }}
                                className="ml-1.5 hover:bg-purple-200 rounded-full p-0.5"
                            >
                                <X className="h-3 w-3" />
                            </button>
                        </span>
                    ))
                ) : (
                    <span className="text-sm text-slate-400 italic">No genetic markers tracked.</span>
                )}
            </div>
        </div>
        
        {/* Extracted Lab Results view in Edit Mode */}
        {formData.lab_results && formData.lab_results.length > 0 && (
            <div className="space-y-3 pt-4 border-t border-slate-100">
                <Label className="flex items-center gap-2 text-blue-700">
                    <Activity className="h-4 w-4" /> Current Lab Results
                </Label>
                <div className="flex flex-col gap-4 max-h-64 overflow-y-auto pr-1">
                    {Object.entries(
                        formData.lab_results.reduce((acc: Record<string, any[]>, lab: any) => {
                            const date = lab.collected_at ? new Date(lab.collected_at).toLocaleDateString() : 'Unknown Date';
                            if (!acc[date]) acc[date] = [];
                            acc[date].push(lab);
                            return acc;
                        }, {})
                    ).map(([date, labs]: [string, any]) => (
                        <div key={date} className="space-y-2">
                            <h4 className="text-xs font-semibold text-slate-500 bg-slate-100 px-2 py-1 rounded">{date}</h4>
                            <div className="flex flex-col gap-2">
                                {labs.map((lab: any, i: number) => (
                                    <div key={i} className="text-xs bg-slate-50 border p-2 rounded flex justify-between items-center group">
                                        <div className="flex flex-col">
                                            <span className="font-medium text-slate-700">{lab.test_name}</span>
                                        </div>
                                        <div className="flex items-center gap-4">
                                            <div className="text-right">
                                                <span className={cn(
                                                    "font-mono font-semibold",
                                                    lab.is_abnormal ? "text-red-600" : "text-slate-600"
                                                )}>
                                                    {lab.value} {lab.unit}
                                                </span>
                                                <div className="text-[10px] text-slate-400">Range: {lab.reference_range}</div>
                                            </div>
                                            {formData.id && lab.id && (
                                                <button
                                                    type="button"
                                                    onClick={async () => {
                                                        try {
                                                            await deleteLabResult(formData.id!, lab.id!)
                                                            setFormData((prev: any) => ({
                                                                ...prev,
                                                                lab_results: prev.lab_results?.filter((l: any) => l.id !== lab.id)
                                                            }))
                                                            toast.success("Lab result removed")
                                                        } catch (e) {
                                                            toast.error("Failed to delete lab result")
                                                        }
                                                    }}
                                                    className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-600 transition-opacity p-1 hover:bg-red-50 rounded"
                                                    title="Delete result"
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        )}

        {/* Labs Scanner - Now fully available for new patients */}
        <div className="space-y-3 pt-4 border-t border-slate-100">
            <Label className="flex items-center gap-2 text-teal-700"><Activity className="h-4 w-4" /> Lab Results Scanner</Label>
            <div className="flex flex-col sm:flex-row gap-2 items-start sm:items-center bg-teal-50/50 p-3 rounded-md border border-teal-100">
                <input type="file" id="lab-image" accept="image/*" className="w-full text-xs flex-1 file:mr-3 file:py-1 file:px-3 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-teal-100 file:text-teal-700 hover:file:bg-teal-200" />
                <Button 
                    type="button"
                    size="sm" 
                    variant="secondary" 
                    className="w-full sm:w-auto bg-white shrink-0"
                    disabled={isScanningLab || (!formData.id && !formData.name && !formData.medical_record_number)}
                    onClick={async () => {
                        const input = document.getElementById("lab-image") as HTMLInputElement
                        const file = input.files?.[0]
                        if (!file) return toast.error("Select an image first")
                        
                        setIsScanningLab(true)
                        toast.info("Scanning lab report...")
                        try {
                            const newLabs = await scanLabResults(file)
                            setFormData(prev => ({
                                ...prev,
                                lab_results: [...(prev.lab_results || []), ...newLabs]
                            }))
                            toast.success(`Successfully extracted ${newLabs.length} biomarkers!`)
                            input.value = ''
                        } catch (e) {
                            console.error(e)
                            toast.error("Failed to scan labs or save patient profile.")
                        } finally {
                            setIsScanningLab(false)
                        }
                    }}
                >
                    {isScanningLab ? "Scanning..." : <><Camera className="h-4 w-4 mr-2" /> Scan Report</>}
                </Button>
            </div>
        </div>
        </div>

        <div className="flex justify-end pt-4 mt-4 border-t">
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
