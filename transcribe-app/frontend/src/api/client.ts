import axios from "axios";

export interface TranscribeOptions {
  model_size?: string;
  language_hint?: string;
  enable_diarization?: boolean;
  enable_punct?: boolean;
  enable_itn?: boolean;
  enable_dialect_map?: boolean;
  custom_lexicon?: string[];
  context_prompt?: string;
}

export interface JobStatus {
  job_id: string;
  status: "pending" | "processing" | "finished" | "failed";
  progress: number;
  error?: string;
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

export async function uploadAudio(file: File, options: TranscribeOptions): Promise<string> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("options", JSON.stringify(options));
  const response = await axios.post("/api/transcribe", formData);
  return response.data.job_id;
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
  const response = await axios.get(`/api/jobs/${jobId}/result`, {
    params: { format },
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
