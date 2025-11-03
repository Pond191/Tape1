export type JobStatusValue = "pending" | "running" | "finished" | "error";

export interface TranscribeOptions {
  model_size?: string;
  enable_dialect_map?: boolean;
}

export interface JobFiles {
  txt: string | null;
  srt: string | null;
  vtt: string | null;
  jsonl: string | null;
}

export interface JobSummary {
  id: string;
  status: JobStatusValue;
}

export interface JobDetail extends JobSummary {
  text?: string | null;
  dialect_text?: string | null;
  error_message?: string | null;
  original_filename?: string | null;
  files: JobFiles;
}

async function parseJson(response: Response) {
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch (err) {
    console.warn("Unable to parse response JSON", err);
    return null;
  }
}

function ensureOk(response: Response, payload: any) {
  if (response.ok) {
    return;
  }
  const message =
    (payload && (payload.message || payload.detail)) ||
    `คำขอไม่สำเร็จ (HTTP ${response.status})`;
  throw new Error(String(message));
}

export async function uploadAudio(file: File, options: TranscribeOptions): Promise<JobSummary> {
  const formData = new FormData();
  formData.append("file", file);
  const model = (options.model_size || "small").toLowerCase();
  formData.append("model_size", model);
  if (typeof options.enable_dialect_map === "boolean") {
    formData.append("enable_dialect_map", String(options.enable_dialect_map));
  }

  const response = await fetch("/api/upload", {
    method: "POST",
    body: formData
  });

  const payload = await parseJson(response);
  ensureOk(response, payload);
  return {
    id: String(payload.id ?? payload.job_id),
    status: (payload?.status as JobStatusValue) || "pending"
  };
}

export async function fetchJob(jobId: string): Promise<JobDetail> {
  const response = await fetch(`/api/jobs/${jobId}`);
  const payload = await parseJson(response);
  ensureOk(response, payload);
  return {
    id: String(payload.id ?? jobId),
    status: (payload?.status as JobStatusValue) || "pending",
    text: payload.text ?? null,
    dialect_text: payload.dialect_text ?? null,
    error_message: payload.error_message ?? null,
    original_filename: payload.original_filename ?? null,
    files: {
      txt: payload.files?.txt ?? null,
      srt: payload.files?.srt ?? null,
      vtt: payload.files?.vtt ?? null,
      jsonl: payload.files?.jsonl ?? null
    }
  };
}

export function downloadFile(url: string | null, filename: string): void {
  if (!url) {
    return;
  }
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", filename);
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  link.remove();
}
