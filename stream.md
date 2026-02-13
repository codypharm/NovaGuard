# Streaming in NovaGuard — A Tutorial

## What Is Streaming?

Without streaming:
```
User sends "hello" → [5-15 seconds of nothing] → Full response appears
```

With streaming:
```
User sends "hello" → "Classifying…" → "Checking FDA…" → "Preparing response…" → Response appears
```

Streaming lets you send **partial results** to the frontend as they happen, instead of waiting for everything to finish.

---

## The 3 Layers

```
┌─────────────────────────────────┐
│  1. LangGraph (astream)         │  ← Produces events
│  2. FastAPI (StreamingResponse) │  ← Transports them as SSE
│  3. React (ReadableStream)      │  ← Consumes and displays them
└─────────────────────────────────┘
```

---

## Layer 1: LangGraph — Producing Events

### Before (one-shot)
```python
# Runs the ENTIRE graph, returns only the final state
result = await workflow.ainvoke(initial_state, config)
```

### After (streaming)
```python
# Yields partial state updates as EACH NODE completes
async for chunk in workflow.astream(initial_state, config, stream_mode="updates"):
    print(chunk)
```

### What does `chunk` look like?

Each chunk is a dict where the key is the node name and the value is what that node changed:

```python
# After gateway_supervisor runs:
{"gateway_supervisor": {"intent": "CLINICAL_QUERY"}}

# After openfda runs:
{"openfda": {"drug_info_map": {"Aspirin": {...}}, "safety_flags": [...]}}

# After assistant_node runs:
{"assistant_node": {"messages": [AIMessage(content="Here is my analysis...")]}}
```

### `stream_mode` options

| Mode | What you get | Use case |
|------|-------------|----------|
| `"updates"` | Only the fields each node changed | Progress tracking (what we use) |
| `"values"` | Full state snapshot after each node | Debugging |
| `"messages"` | LLM tokens as they stream | ChatGPT-like typing effect |

We use `"updates"` because we just need to know **which node finished** and show that to the user.

---

## Layer 2: FastAPI — SSE Transport

### What is SSE (Server-Sent Events)?

SSE is a simple protocol for sending events from server → client over HTTP. Each event is plain text:

```
data: {"event": "progress", "node": "openfda", "label": "Checking FDA…"}\n\n
```

Rules:
- Each line starts with `data: `
- Each event ends with `\n\n` (double newline)
- The payload is JSON

### The FastAPI endpoint

```python
from fastapi.responses import StreamingResponse

@app.post("/clinical-interaction/stream")
async def stream_clinical_interaction(...):
    
    # ═══════════════════════════════════════════
    # PHASE 1: Do all "setup" work here
    # ═══════════════════════════════════════════
    # This runs BEFORE the response is sent.
    # DB queries, auth checks, file reads — all safe here.
    
    image_bytes = await file.read() if file else None
    session = await session_crud.update_session_patient(db, ...)
    workflow = request.app.state.prescription_workflow
    
    # ═══════════════════════════════════════════
    # PHASE 2: The generator (streams to client)
    # ═══════════════════════════════════════════
    # This runs AFTER the response starts.
    # ⚠️ The `db` session is CLOSED by now!
    
    async def event_generator():
        async for chunk in workflow.astream(initial_state, config, stream_mode="updates"):
            for node_name, node_output in chunk.items():
                if node_name.startswith("__"):
                    continue  # Skip LangGraph's internal "__end__" node
                
                label = _NODE_LABELS.get(node_name, "Processing…")
                
                # Format as SSE
                yield f"data: {json.dumps({'event': 'progress', 'label': label})}\n\n"
        
        # Send final result
        yield f"data: {json.dumps({'event': 'complete', 'verdict': ..., 'response': ...})}\n\n"
    
    # Return the stream
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",  # This tells the browser it's SSE
        headers={"Cache-Control": "no-cache"},
    )
```

### ⚠️ The #1 Gotcha: Dependency Lifecycle

This is the trap we fell into. FastAPI's `Depends()` objects have a lifecycle:

```
1. Request comes in
2. FastAPI resolves Depends() → creates db session, authenticates user
3. Your endpoint function runs → returns StreamingResponse
4. FastAPI CLOSES the Depends() objects (db session closed!) ← HERE
5. The generator inside StreamingResponse keeps running
6. Generator tries to use `db` → 💥 silent failure
```

**The rule:** Never use `db` or `current_user` inside the generator. Instead:

```python
# ✅ CORRECT: Capture values BEFORE the generator
workflow = request.app.state.prescription_workflow  # Grab reference
_user_id = current_user.id                          # Copy the string

async def event_generator():
    # Use workflow and _user_id here — they're just regular objects
    ...

# ❌ WRONG: Using Depends objects inside the generator
async def event_generator():
    await db.execute(...)        # 💥 db session is closed
    user = current_user.email    # 💥 might work, might not
```

If you need DB access inside the generator (like for audit logging), create a **new session**:

```python
async def event_generator():
    ...
    finally:
        from nova_guard.database import AsyncSessionLocal
        async with AsyncSessionLocal() as fresh_db:
            await save_audit_log(fresh_db, ...)
```

---

## Layer 3: React — Consuming the Stream

### Why not EventSource?

The browser has a built-in `EventSource` API for SSE, but it **only supports GET requests**. We need POST because we send FormData (with file uploads). So we use `fetch()` + `ReadableStream`.

### The consumer function

```typescript
async function streamClinicalInteraction(
    sessionId: string, text: string, file: File | null,
    callbacks: {
        onProgress?: (event) => void,
        onComplete?: (event) => void,
        onError?: (event) => void,
    }
) {
    // 1. Send the POST request
    const res = await fetch("/clinical-interaction/stream", {
        method: "POST",
        body: formData,
    })

    // 2. Get a reader for the response body stream
    const reader = res.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ""

    // 3. Read chunks as they arrive
    while (true) {
        const { done, value } = await reader.read()
        if (done) break

        // Decode bytes → string, append to buffer
        buffer += decoder.decode(value, { stream: true })

        // 4. Split on double newlines (SSE event boundary)
        const parts = buffer.split("\n\n")
        buffer = parts.pop() || ""  // Last part might be incomplete

        // 5. Parse each complete event
        for (const part of parts) {
            const line = part.trim()
            if (!line.startsWith("data: ")) continue

            const event = JSON.parse(line.slice(6))  // Remove "data: " prefix
            //                              ^^^^^^
            //                              "data: " is 6 characters

            switch (event.event) {
                case "progress": callbacks.onProgress?.(event); break
                case "complete": callbacks.onComplete?.(event); break
                case "error":    callbacks.onError?.(event);    break
            }
        }
    }
}
```

### Why the buffer?

Network data arrives in arbitrary chunks. One `reader.read()` might give you:

```
// Chunk 1:
"data: {\"event\":\"progress\",\"label\":\"Classif"

// Chunk 2:
"ying…\"}\n\ndata: {\"event\":\"progress\",\"label\":\"Checking FDA…\"}\n\n"
```

The buffer collects data and only processes **complete events** (terminated by `\n\n`). The incomplete tail stays in the buffer for the next iteration.

### React component wiring

```tsx
// SafetyHUD.tsx
const [processingStep, setProcessingStep] = useState<string | null>(null)

await streamClinicalInteraction(sessionId, text, file, {
    onProgress: (e) => setProcessingStep(e.label),     // Updates live
    onComplete: (e) => {
        setVerdict(e.verdict)
        setAssistantResponse(e.assistant_response)
    },
    onError: (e) => setAssistantResponse(`⚠️ ${e.message}`),
})

setProcessingStep(null)  // Clear when done
```

```tsx
// SafetyChat.tsx — the processing indicator
{isProcessing && (
    <div>
        {processingStep && (
            <span className="text-teal-600 animate-pulse">
                {processingStep}  {/* "Checking FDA safety database…" */}
            </span>
        )}
        <BouncingDots />
    </div>
)}
```

---

## Event Types Reference

| Event | When | Payload |
|-------|------|---------|
| `progress` | Each graph node completes | `{event, node, label}` |
| `complete` | Workflow finished | `{event, status, intent, verdict, assistant_response, safety_flags}` |
| `error` | Something failed | `{event, message, detail?}` |

---

## Phase 2 (Future): Token-Level Streaming

Right now we stream **per-node** — the user sees which step is running. Phase 2 would add **per-token** streaming for the assistant response (ChatGPT-like typing effect).

This requires:
1. Changing `stream_mode` to `"messages"` or using `astream_events()`
2. Modifying `bedrock_client.chat()` to pass `stream=True`
3. Frontend accumulating tokens character by character

Not implemented yet, but the SSE infrastructure we built supports it — just add a new event type like `{event: "token", content: "The "}`.
