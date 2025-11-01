import axios from "axios";

export interface TranscribeOptions {
  model_size?: string;
  language_hint?: string;
  enable_diarization?: boolean;
  enable_punct?: boolean;
  enable_itn?: boolean;
  enable_dialect_map?: boolean;
}

export interface JobStatus {
  job_id: string;
  status: "pending" | "processing" | "finished" | "failed";
  progress: number;
  error?: string;
  text?: string | null;
  output_txt_path?: string | null;
  output_srt_path?: string | null;
  output_vtt_path?: string | null;
  output_jsonl_path?: string | null;
}

export interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
  speaker?: string;
}

export interface JobResult {
  job_id: string;
  text: string;
  segments: TranscriptSegment[];
  dialect_mapped_text?: string | null;
}

async function safeJson(response: Response): Promise<any | null> {
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch (err) {
    console.warn("Unable to parse error payload", err);
    return null;
  }
}

export async function uploadAudio(file: File, options: TranscribeOptions): Promise<string> {
  const formData = new FormData();
  formData.append("file", file);

  const modelSize = options.model_size ?? "small";
  formData.append("model_size", modelSize);

  const appendBoolean = (key: string, value: boolean | undefined) => {
    if (typeof value === "boolean") {
      formData.append(key, String(value));
    }
  };

  if (options.language_hint) {
    formData.append("language_hint", options.language_hint);
  }
  appendBoolean("enable_dialect_map", options.enable_dialect_map);
  appendBoolean("enable_diarization", options.enable_diarization);
  appendBoolean("enable_punct", options.enable_punct);
  appendBoolean("enable_itn", options.enable_itn);

  const response = await fetch("/api/upload", {
    method: "POST",
    body: formData
  });

  if (!response.ok) {
    const errorPayload = await safeJson(response);
    const message =
      (errorPayload?.message && String(errorPayload.message)) ||
      (errorPayload?.detail && String(errorPayload.detail)) ||
      `อัปโหลดไม่สำเร็จ (HTTP ${response.status})`;
    throw new Error(message);
  }

  const data = await response.json();
  return data.job_id as string;
}

export async function fetchJob(jobId: string): Promise<JobStatus> {
  const response = await axios.get(`/api/jobs/${jobId}`);
  return response.data;
}

export async function fetchResult(jobId: string): Promise<JobResult> {
  const response = await axios.get(`/api/jobs/${jobId}/result/inline`);
  return response.data;
}

export async function downloadResult(jobId: string, format: string): Promise<void> {
  const endpointMap: Record<string, string> = {
    txt: "txt",
    srt: "srt",
    vtt: "vtt",
    jsonl: "jsonl"
  };
  const endpoint = endpointMap[format] || `result?format=${format}`;
  const response = await axios.get(`/api/jobs/${jobId}/${endpoint}`, {
    responseType: "blob"
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", `${jobId}.${format}`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
