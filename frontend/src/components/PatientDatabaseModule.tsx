import { useState, useEffect } from "react"
import { useSessionContext } from "@/context/SessionContext"
import { getPatients, scanLabResults, saveLabResult, type Patient } from "@/services/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Search, Stethoscope, User, Loader2, Camera, ChevronDown, ChevronRight } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"

export default function PatientDatabaseModule() {
  const { createNewSession, setActiveModule } = useSessionContext()
  const [patients, setPatients] = useState<Patient[]>([])
  const [loading, setLoading] = useState(true)
  const [startingPatientId, setStartingPatientId] = useState<number | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null)
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
    loadPatients()
  }, [])

  const loadPatients = async () => {
    try {
      setLoading(true)
      const data = await getPatients()
      setPatients(data)
    } catch (err) {
      console.error("Failed to load patients", err)
    } finally {
      setLoading(false)
    }
  }

  const handleStartCheck = async (patient: Patient) => {
    try {
        setStartingPatientId(patient.id)
        // 1. Create new session linked to this patient
        await createNewSession(patient.id)
        // context automatically switches session
        
        // 2. Switch view to Chat
        setActiveModule('safety-check')
    } catch (err) {
        console.error("Failed to start session", err)
    } finally {
        setStartingPatientId(null)
    }
  }

  const filteredPatients = patients.filter(p => 
    (p.name || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
    (p.medical_record_number && p.medical_record_number.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  const formatDate = (dateString: string) => {
      if (!dateString) return "N/A"
      try {
          return new Date(dateString).toLocaleDateString(undefined, {
              year: 'numeric',
              month: 'long',
              day: 'numeric'
          })
      } catch (e) {
          return dateString
      }
  }

  if (selectedPatient) {
      return (
          <div className="p-6 space-y-6 max-w-5xl mx-auto">
              {/* Header with Back Button */}
              <div className="flex items-center gap-4">
                  <Button variant="ghost" onClick={() => setSelectedPatient(null)} className="gap-2">
                       ← Back to List
                  </Button>
                  <h1 className="text-2xl font-bold">{selectedPatient.name}</h1>
                  {selectedPatient.medical_record_number && (
                      <Badge variant="outline" className="font-mono">{selectedPatient.medical_record_number}</Badge>
                  )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* Left Column: Demographics & Actions */}
                  <div className="space-y-6">
                      <Card>
                          <CardHeader>
                              <CardTitle className="text-lg">Quick Actions</CardTitle>
                          </CardHeader>
                          <CardContent className="space-y-3">
                                <Button 
                                  className="w-full bg-teal-600 hover:bg-teal-700" 
                                  onClick={() => handleStartCheck(selectedPatient)}
                                  disabled={startingPatientId === selectedPatient.id}
                                >
                                    {startingPatientId === selectedPatient.id ? (
                                        <>
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                            Starting...
                                        </>
                                    ) : (
                                        <>
                                            <Stethoscope className="mr-2 h-4 w-4" />
                                            Start Safety Check
                                        </>
                                    )}
                                </Button>

                          </CardContent>
                      </Card>

                      <Card>
                          <CardHeader>
                              <CardTitle className="flex items-center gap-2 text-lg">
                                  <Camera className="h-5 w-5 text-blue-600" />
                                  Upload Lab Report
                              </CardTitle>
                          </CardHeader>
                          <CardContent>
                              <div className="flex flex-col gap-3">
                                  <input 
                                      type="file" 
                                      id="lab-image-db" 
                                      accept="image/*" 
                                      className="text-xs file:mr-3 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100" 
                                  />
                                  <Button 
                                      className="w-full bg-blue-600 hover:bg-blue-700" 
                                      disabled={isScanningLab}
                                      onClick={async () => {
                                          const input = document.getElementById("lab-image-db") as HTMLInputElement
                                          const file = input.files?.[0]
                                          if (!file) return toast.error("Select an image first")
                                          
                                          setIsScanningLab(true)
                                          toast.info("Scanning lab report...")
                                          try {
                                              const newLabs = await scanLabResults(file)
                                              toast.success(`Successfully extracted ${newLabs.length} biomarkers!`)
                                              input.value = ''
                                              
                                              // Save each lab result to the patient
                                              for (const lab of newLabs) {
                                                  await saveLabResult(selectedPatient.id, lab)
                                              }
                                              
                                              // Update local state so it appears immediately
                                              setSelectedPatient({
                                                  ...selectedPatient,
                                                  lab_results: [...(selectedPatient.lab_results || []), ...newLabs]
                                              })
                                              // Refresh list silently
                                              const data = await getPatients()
                                              setPatients(data)
                                          } catch (e) {
                                              toast.error("Failed to scan labs")
                                          } finally {
                                              setIsScanningLab(false)
                                          }
                                      }}
                                  >
                                      {isScanningLab ? (
                                          <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Scanning...</>
                                      ) : (
                                          <><Camera className="mr-2 h-4 w-4" /> Scan Report</>
                                      )}
                                  </Button>
                              </div>
                          </CardContent>
                      </Card>

                      <Card>
                          <CardHeader>
                              <CardTitle className="text-lg">Vitals & Demographics</CardTitle>
                          </CardHeader>
                          <CardContent className="space-y-4 text-sm">
                              <div className="grid grid-cols-2 gap-2">
                                  <span className="text-slate-500">Date of Birth:</span>
                                  <span className="font-medium">
                                      {selectedPatient.date_of_birth ? formatDate(selectedPatient.date_of_birth) : 'N/A'}
                                  </span>
                                  
                                  <span className="text-slate-500">Age:</span>
                                  <span className="font-medium">
                                      {selectedPatient.date_of_birth ? `${new Date().getFullYear() - new Date(selectedPatient.date_of_birth).getFullYear()} yrs` : (selectedPatient.age_years ? `${selectedPatient.age_years} yrs` : 'N/A')}
                                  </span>
                                  
                                  <span className="text-slate-500">Weight:</span>
                                  <span className="font-medium">{selectedPatient.weight ? `${selectedPatient.weight} kg` : 'N/A'}</span>
                                  
                                  <span className="text-slate-500">Height:</span>
                                  <span className="font-medium">{selectedPatient.height ? `${selectedPatient.height} cm` : 'N/A'}</span>
                              </div>
                              
                              <div className="pt-2 border-t space-y-1">
                                  {selectedPatient.is_pregnant && (
                                      <div className="flex items-center text-amber-600 font-medium py-1">
                                          <User className="h-4 w-4 mr-2" /> Pregnant
                                      </div>
                                  )}
                                  {selectedPatient.is_nursing && (
                                      <div className="flex items-center text-amber-600 font-medium py-1">
                                          <User className="h-4 w-4 mr-2" /> Nursing
                                      </div>
                                  )}
                              </div>
                          </CardContent>
                      </Card>
                  </div>

                  {/* Right Column: Clinical Data */}
                  <div className="md:col-span-2 space-y-6">
                      <Card>
                          <CardHeader>
                              <CardTitle className="flex items-center gap-2">
                                  <span className="inline-block w-2 h-2 rounded-full bg-rose-500" />
                                  Allergies
                              </CardTitle>
                          </CardHeader>
                          <CardContent>
                              {selectedPatient.allergies && selectedPatient.allergies.length > 0 ? (
                                  <div className="flex flex-wrap gap-2">
                                      {selectedPatient.allergies.map((a, i) => (
                                          <Badge key={i} variant="secondary" className="bg-rose-50 text-rose-700 border-rose-200 hover:bg-rose-100">
                                              {a.allergen}
                                              {a.severity && <span className="ml-1 opacity-70">({a.severity})</span>}
                                          </Badge>
                                      ))}
                                  </div>
                              ) : (
                                  <p className="text-slate-400 italic">No known allergies recorded.</p>
                              )}
                          </CardContent>
                      </Card>

                       <Card>
                           <CardHeader>
                               <CardTitle className="flex items-center gap-2">
                                   <span className="inline-block w-2 h-2 rounded-full bg-amber-500" />
                                   Drug History
                               </CardTitle>
                           </CardHeader>
                           <CardContent>
                               {selectedPatient.drug_history && selectedPatient.drug_history.length > 0 ? (
                                   <div className="flex flex-col gap-3">
                                       {Object.entries(
                                           selectedPatient.drug_history.reduce((acc: Record<string, any[]>, drug: any) => {
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
                                                                       <span className="text-[10px] text-slate-500">{drug.dose || ''} {drug.dose && drug.frequency ? '•' : ''} {drug.frequency || ''}</span>
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
                                       ))}
                                   </div>
                               ) : (
                                   <p className="text-slate-400 italic">No drug history recorded.</p>
                               )}
                           </CardContent>
                       </Card>

                      <Card>
                           <CardHeader>
                               <CardTitle className="flex items-center gap-2">
                                   <span className="inline-block w-2 h-2 rounded-full bg-purple-500" />
                                   Pharmacogenomics (PGx)
                               </CardTitle>
                           </CardHeader>
                           <CardContent>
                               {selectedPatient.genetic_markers && selectedPatient.genetic_markers.length > 0 ? (
                                   <div className="flex flex-wrap gap-2">
                                       {selectedPatient.genetic_markers.map((marker, i) => (
                                           <Badge key={i} variant="secondary" className="bg-purple-50 text-purple-800 border-purple-200 hover:bg-purple-100">
                                               <span className="font-bold mr-1">{marker.gene}:</span> {marker.phenotype}
                                           </Badge>
                                       ))}
                                   </div>
                               ) : (
                                   <p className="text-slate-400 italic">No genetic markers tracked.</p>
                               )}
                           </CardContent>
                       </Card>

                       <Card>
                           <CardHeader>
                               <CardTitle className="flex items-center gap-2">
                                   <span className="inline-block w-2 h-2 rounded-full bg-blue-500" />
                                   Lab Results
                               </CardTitle>
                           </CardHeader>
                           <CardContent>
                               {selectedPatient.lab_results && selectedPatient.lab_results.length > 0 ? (
                                   <div className="flex flex-col gap-3">
                                       {Object.entries(
                                           selectedPatient.lab_results.reduce((acc: Record<string, any[]>, lab: any) => {
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
                                       ))}
                                   </div>
                               ) : (
                                   <p className="text-slate-400 italic">No lab results on file.</p>
                               )}
                           </CardContent>
                       </Card>
                   </div>
               </div>
           </div>
       )
   }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">Patient Database</h1>
          <p className="text-slate-500 mt-1">Manage patient profiles and history.</p>
        </div>

      </div>

      <div className="mb-6 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input 
            placeholder="Type to search patients..."  
            className="pl-10 h-12 text-lg"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
      </div>

      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
          <Table>
              <TableHeader className="bg-slate-50">
                  <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>MRN</TableHead>
                      <TableHead>Date of Birth</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
              </TableHeader>
              <TableBody>
                  {loading ? (
                      <TableRow>
                          <TableCell colSpan={5} className="h-24 text-center text-slate-400">
                              Loading patients...
                          </TableCell>
                      </TableRow>
                  ) : filteredPatients.length === 0 ? (
                      <TableRow>
                          <TableCell colSpan={5} className="h-24 text-center text-slate-400">
                              No patients found matching "{searchQuery}"
                          </TableCell>
                      </TableRow>
                  ) : (
                      filteredPatients.map((patient) => (
                          <TableRow 
                            key={patient.id} 
                            className="group cursor-pointer hover:bg-slate-50"
                            onClick={() => setSelectedPatient(patient)}
                          >
                              <TableCell className="font-medium text-slate-900">
                                  {patient.name}
                              </TableCell>
                              <TableCell className="font-mono text-xs text-slate-500">
                                  {patient.medical_record_number || "—"}
                              </TableCell>
                              <TableCell>
                                  {patient.date_of_birth ? formatDate(patient.date_of_birth) : "—"}
                              </TableCell>
                              <TableCell>
                                  <div className="flex flex-wrap gap-1">
                                    {patient.is_pregnant && <Badge variant="secondary" className="bg-rose-100 text-rose-700 text-[10px] h-5 px-1.5">Pregnant</Badge>}
                                    {patient.is_nursing && <Badge variant="secondary" className="bg-amber-100 text-amber-700 text-[10px] h-5 px-1.5">Nursing</Badge>}
                                    {patient.allergies && patient.allergies.length > 0 && <Badge variant="outline" className="text-[10px] h-5 px-1.5 border-rose-200 text-rose-700">{patient.allergies.length} Allergies</Badge>}
                                    {patient.genetic_markers && patient.genetic_markers.length > 0 && <Badge variant="secondary" className="bg-purple-100 text-purple-700 text-[10px] h-5 px-1.5">PGx</Badge>}
                                    {(!patient.is_pregnant && !patient.is_nursing && (!patient.allergies || patient.allergies.length === 0) && (!patient.genetic_markers || patient.genetic_markers.length === 0)) && (
                                        <Badge variant="secondary" className="bg-slate-100 text-slate-500 text-[10px] h-5 px-1.5 font-normal">Active</Badge>
                                    )}
                                  </div>
                              </TableCell>
                              <TableCell className="text-right">
                                  <Button 
                                    size="sm" 
                                    variant="ghost" 
                                    className="opacity-0 group-hover:opacity-100 transition-opacity"
                                    onClick={(e) => {
                                        e.stopPropagation()
                                        handleStartCheck(patient)
                                    }}
                                    disabled={startingPatientId === patient.id}
                                  >
                                      {startingPatientId === patient.id ? (
                                          <Loader2 className="h-4 w-4 mr-2 text-teal-600 animate-spin" />
                                      ) : (
                                          <Stethoscope className="h-4 w-4 mr-2 text-teal-600" />
                                      )}
                                      Check
                                  </Button>
                              </TableCell>
                          </TableRow>
                      ))
                  )}
              </TableBody>
          </Table>
      </div>
    </div>
  )
}
