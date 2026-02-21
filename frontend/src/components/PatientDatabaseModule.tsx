import { useState, useEffect } from "react"
import { useSessionContext } from "@/context/SessionContext"
import { getPatients, scanLabResults, type Patient } from "@/services/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Search, Stethoscope, User, Loader2, Camera } from "lucide-react"
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
                                              const newLabs = await scanLabResults(selectedPatient.id, file)
                                              toast.success(`Successfully extracted ${newLabs.length} biomarkers!`)
                                              input.value = ''
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
                                  <span className="font-medium">{selectedPatient.age_years ? `${selectedPatient.age_years} yrs` : 'N/A'}</span>
                                  
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
                                  Medical History
                              </CardTitle>
                          </CardHeader>
                          <CardContent>
                              {selectedPatient.medical_history && selectedPatient.medical_history.length > 0 ? (
                                  <div className="flex flex-wrap gap-2">
                                      {selectedPatient.medical_history.map((c, i) => (
                                          <Badge key={i} variant="outline" className="border-amber-200 bg-amber-50 text-amber-700">
                                              {c.condition}
                                          </Badge>
                                      ))}
                                  </div>
                              ) : (
                                  <p className="text-slate-400 italic">No medical history recorded.</p>
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
