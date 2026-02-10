const API_URL = "http://localhost:8000"

export interface Patient {
  id: number
  name: string
  date_of_birth: string
  medical_record_number?: string
  weight?: string
  height?: string
  allergies: Allergy[]
  medical_history?: Condition[]
}

export interface Allergy {
  allergen: string
  severity: string
}

export interface Condition {
  condition: string
}

export interface ProcessResponse {
    status: string
    verdict: {
        status: "green" | "yellow" | "red"
        flags: any[]
    }
    extracted_data: any
}

export async function getPatient(id: number): Promise<Patient> {
  const res = await fetch(`${API_URL}/patients/${id}`)
  if (!res.ok) throw new Error("Failed to fetch patient")
  return res.json()
}

export async function processPrescription(patientId: number, text: string, file: File | null): Promise<ProcessResponse> {
    const formData = new FormData()
    formData.append("patient_id", patientId.toString())
    formData.append("input_type", file ? "image" : "text")
    if (text) formData.append("prescription_text", text)
    if (file) formData.append("file", file)

    const res = await fetch(`${API_URL}/prescriptions/process`, {
        method: "POST",
        body: formData
    })
    
    if (!res.ok) {
        const err = await res.text()
        throw new Error(err || "Failed to process prescription")
    }
    
    return res.json()
}

export async function createPatient(data: Partial<Patient>): Promise<Patient> {
    const res = await fetch(`${API_URL}/patients`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    })
    if (!res.ok) throw new Error("Failed to create patient")
    return res.json()
}

export async function addAllergy(patientId: number, allergen: string): Promise<void> {
    await fetch(`${API_URL}/patients/${patientId}/allergies`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            patient_id: patientId,
            allergen: allergen,
            allergy_type: "drug", // Defaulting for simple UI
            severity: "severe"    // Defaulting for safety
        })
    })
}

export async function getPatientByMRN(mrn: string): Promise<Patient | null> {
    const res = await fetch(`${API_URL}/patients/lookup/${mrn}`)
    if (res.status === 404) return null
    if (!res.ok) throw new Error("Failed to lookup patient")
    return res.json()
}
