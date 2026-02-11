const API_URL = "http://localhost:8000"

export interface Patient {
  id: number
  name: string
  date_of_birth: string
  medical_record_number?: string
  weight?: string
  height?: string
  age_years?: number
  is_pregnant?: boolean
  is_nursing?: boolean
  egfr?: number
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
    intent?: string
    assistant_response?: string
    external_url?: string
    verdict?: {
        status: "green" | "yellow" | "red"
        flags: any[]
    }
    safety_flags?: any[]
    extracted_data: any
}

export async function getPatient(id: number): Promise<Patient> {
  const res = await fetch(`${API_URL}/patients/${id}`)
  if (!res.ok) throw new Error("Failed to fetch patient")
  return res.json()
}

export async function processClinicalInteraction(
    sessionId: string,
    patientId: number | null,
    text: string,
    file: File | null
): Promise<ProcessResponse> {
    const formData = new FormData()
    formData.append("session_id", sessionId)
    if (patientId) formData.append("patient_id", patientId.toString())
    formData.append("input_type", file ? "image" : "text")
    if (text) formData.append("prescription_text", text)
    if (file) formData.append("file", file)

    const res = await fetch(`${API_URL}/clinical-interaction/process`, {
        method: "POST",
        body: formData
    })
    
    if (!res.ok) {
        const err = await res.text()
        throw new Error(err || "Failed to process clinical interaction")
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

export async function updatePatient(id: number, data: Partial<Patient>): Promise<Patient> {
    const res = await fetch(`${API_URL}/patients/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    })
    if (!res.ok) throw new Error("Failed to update patient")
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

export interface Session {
    id: string
    title: string
    updated_at: string
    patient?: Patient
}

export async function getSessions(limit: number = 20): Promise<Session[]> {
    const res = await fetch(`${API_URL}/sessions?limit=${limit}`)
    if (!res.ok) throw new Error("Failed to fetch sessions")
    return res.json()
}

export async function createSession(sessionId: string): Promise<void> {
    const formData = new FormData()
    formData.append("session_id", sessionId)
    
    const res = await fetch(`${API_URL}/sessions`, {
        method: "POST",
        body: formData
    })
    
    if (!res.ok) throw new Error("Failed to create session")
}

export async function deleteSession(sessionId: string): Promise<void> {
    const res = await fetch(`${API_URL}/sessions/${sessionId}`, {
        method: "DELETE"
    })
    
    if (!res.ok) throw new Error("Failed to delete session")
}

export interface ChatMessage {
    id: string
    role: 'user' | 'assistant'
    content: string
    timestamp?: string
}

export async function getSessionHistory(sessionId: string): Promise<ChatMessage[]> {
    const res = await fetch(`${API_URL}/sessions/${sessionId}/history`)
    if (!res.ok) return []
    return res.json()
}
