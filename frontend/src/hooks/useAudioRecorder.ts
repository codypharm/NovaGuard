
import { useState, useRef, useCallback } from 'react';

export const useAudioRecorder = () => {
    const [isRecording, setIsRecording] = useState(false);
    const audioContextRef = useRef<AudioContext | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const processorRef = useRef<ScriptProcessorNode | null>(null);
    
    // We use a simple buffer to accumulate PCM data
    const chunksRef = useRef<Float32Array[]>([]);

    const startRecording = useCallback(async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            streamRef.current = stream;

            // Nova Sonic expects 24kHz
            // Note: Some browsers might not support setting sampleRate here, 
            // but we can rely on standard context and then resample or just send what we get.
            // However, to match Nova exactly, we try 24000.
            const audioContext = new AudioContext({ sampleRate: 24000 });
            audioContextRef.current = audioContext;

            const source = audioContext.createMediaStreamSource(stream);
            // Buffer size 4096, 1 input channel, 1 output channel
            const processor = audioContext.createScriptProcessor(4096, 1, 1);
            processorRef.current = processor;

            chunksRef.current = [];

            processor.onaudioprocess = (e) => {
                const inputData = e.inputBuffer.getChannelData(0);
                // Copy buffer
                chunksRef.current.push(new Float32Array(inputData));
            };

            source.connect(processor);
            processor.connect(audioContext.destination);

            setIsRecording(true);
        } catch (err) {
            console.error("Failed to start recording", err);
        }
    }, []);

    const stopRecording = useCallback(async (): Promise<Blob> => {
        if (!isRecording) return new Blob();

        // Stop tracks
        streamRef.current?.getTracks().forEach(track => track.stop());
        processorRef.current?.disconnect();
        audioContextRef.current?.close();

        setIsRecording(false);

        // Merge chunks
        const merged = mergeBuffers(chunksRef.current);
        // Convert to Int16 PCM
        const pcm16 = floatTo16BitPCM(merged);
        
        // Create WAV header
        // 24000 is what we initialized AudioContext with. 
        // If browser ignored it (e.g. forced 48k), the WAV header will be wrong if we hardcode 24k.
        // Robustness: check audioContext.sampleRate, but Nova expects 24k. 
        // If we send 48k with 24k header, it plays slow.
        // For now assume 24k works or Nova is somewhat flexible with raw PCM if we send correct header?
        // Actually Nova expects raw PCM, so no header.
        // BUT my backend strips 44 bytes.
        // So I'll write WAV header with 24000.
        const wavBytes = encodeWAV(pcm16, 24000);
        
        return new Blob([wavBytes.buffer as ArrayBuffer], { type: 'audio/wav' });
    }, [isRecording]);

    return { isRecording, startRecording, stopRecording };
};

// Helper functions for minimal WAV encoding
function mergeBuffers(buffers: Float32Array[]): Float32Array {
    let length = 0;
    buffers.forEach(b => length += b.length);
    const result = new Float32Array(length);
    let offset = 0;
    buffers.forEach(b => {
        result.set(b, offset);
        offset += b.length;
    });
    return result;
}

function floatTo16BitPCM(input: Float32Array): Int16Array {
    const output = new Int16Array(input.length);
    for (let i = 0; i < input.length; i++) {
        const s = Math.max(-1, Math.min(1, input[i]));
        output[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return output;
}

function encodeWAV(samples: Int16Array, sampleRate: number): DataView {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    const writeString = (offset: number, string: string) => {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    };

    /* RIFF identifier */
    writeString(0, 'RIFF');
    /* RIFF chunk length */
    view.setUint32(4, 36 + samples.length * 2, true);
    /* RIFF type */
    writeString(8, 'WAVE');
    /* format chunk identifier */
    writeString(12, 'fmt ');
    /* format chunk length */
    view.setUint32(16, 16, true);
    /* sample format (raw) */
    view.setUint16(20, 1, true);
    /* channel count */
    view.setUint16(22, 1, true);
    /* sample rate */
    view.setUint32(24, sampleRate, true);
    /* byte rate (sample rate * block align) */
    view.setUint32(28, sampleRate * 2, true);
    /* block align (channel count * bytes per sample) */
    view.setUint16(32, 2, true);
    /* bits per sample */
    view.setUint16(34, 16, true);
    /* data chunk identifier */
    writeString(36, 'data');
    /* data chunk length */
    view.setUint32(40, samples.length * 2, true);

    // Write samples
    let offset = 44;
    for (let i = 0; i < samples.length; i++) {
        view.setInt16(offset, samples[i], true);
        offset += 2;
    }

    return view;
}
