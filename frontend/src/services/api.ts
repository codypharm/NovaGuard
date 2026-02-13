const API_URL = "http://localhost:8000"

let getToken: (() => Promise<string | null>) | null = null;

export function setTokenProvider(provider: () => Promise<string | null>) {
    getToken = provider;
}

async function getAuthHeaders(): Promise<HeadersInit> {
    const headers: HeadersInit = {};
    if (getToken) {
        const token = await getToken();
        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }
    }
    return headers;
}

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
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_URL}/patients/${id}`, { headers })
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

    
    // FormData doesn't need Content-Type header (browser sets it)
    // But we need to spread existing headers if we were using a simple dict, 
    // however HeadersInit type + FormData is tricky if we manually set Content-Type.
    // For Authorization we just add it.
    
    // We need to pass the headers object but fetch expects HeadersInit.
    // We can't easily spread headers into the options if it's not already an object.
    
    const reqHeaders: any = await getAuthHeaders();

    const res = await fetch(`${API_URL}/clinical-interaction/process`, {
        method: "POST",
        headers: reqHeaders,
        body: formData
    })
    
    if (!res.ok) {
        const err = await res.text()
        throw new Error(err || "Failed to process clinical interaction")
    }
    
    return res.json()
}

// ============================================================================
// Streaming API (SSE via fetch + ReadableStream)
// ============================================================================

export interface StreamProgressEvent {
    event: "progress"
    node: string
    label: string
}

export interface StreamCompleteEvent {
    event: "complete"
    status: string
    intent?: string
    verdict?: ProcessResponse["verdict"]
    assistant_response?: string
    safety_flags?: any[]
}

export interface StreamErrorEvent {
    event: "error"
    message: string
    detail?: string
}

export type StreamEvent = StreamProgressEvent | StreamCompleteEvent | StreamErrorEvent

export interface StreamCallbacks {
    onProgress?: (event: StreamProgressEvent) => void
    onComplete?: (event: StreamCompleteEvent) => void
    onError?: (event: StreamErrorEvent) => void
}

/**
 * Streams clinical interaction results via SSE.
 * Uses fetch + ReadableStream (not EventSource) to support POST + FormData.
 */
export async function streamClinicalInteraction(
    sessionId: string,
    patientId: number | null,
    text: string,
    file: File | null,
    callbacks: StreamCallbacks,
): Promise<void> {
    const formData = new FormData()
    formData.append("session_id", sessionId)
    if (patientId) formData.append("patient_id", patientId.toString())
    formData.append("input_type", file ? "image" : "text")
    if (text) formData.append("prescription_text", text)
    if (file) formData.append("file", file)

    const reqHeaders: any = await getAuthHeaders()

    const res = await fetch(`${API_URL}/clinical-interaction/stream`, {
        method: "POST",
        headers: reqHeaders,
        body: formData,
    })

    if (!res.ok) {
        const err = await res.text()
        throw new Error(err || "Stream request failed")
    }

    const reader = res.body?.getReader()
    if (!reader) throw new Error("No readable stream available")

    const decoder = new TextDecoder()
    let buffer = ""

    while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // SSE events are separated by double newlines
        const parts = buffer.split("\n\n")
        buffer = parts.pop() || "" // Keep incomplete last chunk in buffer

        for (const part of parts) {
            const line = part.trim()
            if (!line.startsWith("data: ")) continue

            try {
                const event: StreamEvent = JSON.parse(line.slice(6))

                switch (event.event) {
                    case "progress":
                        callbacks.onProgress?.(event)
                        break
                    case "complete":
                        callbacks.onComplete?.(event)
                        break
                    case "error":
                        callbacks.onError?.(event)
                        break
                }
            } catch {
                console.warn("Failed to parse SSE event:", line)
            }
        }
    }
}

export async function createPatient(data: Partial<Patient>): Promise<Patient> {
    const headers: any = await getAuthHeaders();
    headers["Content-Type"] = "application/json";

    const res = await fetch(`${API_URL}/patients`, {
        method: "POST",
        headers: headers,
        body: JSON.stringify(data)
    })
    if (!res.ok) throw new Error("Failed to create patient")
    return res.json()
}

export async function updatePatient(id: number, data: Partial<Patient>): Promise<Patient> {
    const headers: any = await getAuthHeaders();
    headers["Content-Type"] = "application/json";

    const res = await fetch(`${API_URL}/patients/${id}`, {
        method: "PUT",
        headers: headers,
        body: JSON.stringify(data)
    })
    if (!res.ok) throw new Error("Failed to update patient")
    return res.json()
}

export async function addAllergy(patientId: number, allergen: string): Promise<void> {
    const headers: any = await getAuthHeaders();
    headers["Content-Type"] = "application/json";

    await fetch(`${API_URL}/patients/${patientId}/allergies`, {
        method: "POST",
        headers: headers,
        body: JSON.stringify({
            patient_id: patientId,
            allergen: allergen,
            allergy_type: "drug", // Defaulting for simple UI
            severity: "severe"    // Defaulting for safety
        })
    })
}

export async function getPatientByMRN(mrn: string): Promise<Patient | null> {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_URL}/patients/lookup/${mrn}`, { headers })
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
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_URL}/sessions?limit=${limit}`, { headers })
    if (!res.ok) throw new Error("Failed to fetch sessions")
    return res.json()
}

export async function createSession(sessionId: string): Promise<void> {
    const formData = new FormData()
    formData.append("session_id", sessionId)
    
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_URL}/sessions`, {
        method: "POST",
        headers: headers,
        body: formData
    })
    
    if (!res.ok) throw new Error("Failed to create session")
}

export async function deleteSession(sessionId: string): Promise<void> {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_URL}/sessions/${sessionId}`, {
        method: "DELETE",
        headers: headers
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
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_URL}/sessions/${sessionId}/history`, { headers })
    if (!res.ok) return []
    return res.json()
}
