import { Dispatch, SetStateAction, useEffect, useMemo } from "react";

import {
  JobDetail,
  JobStatusValue,
  downloadFile,
  fetchJob
} from "../api/client";

interface Props {
  jobs: JobDetail[];
  setJobs: Dispatch<SetStateAction<JobDetail[]>>;
}

const STATUS_LABELS: Record<JobStatusValue, string> = {
  pending: "รอคิว",
  running: "กำลังประมวลผล",
  finished: "เสร็จสมบูรณ์",
  error: "เกิดข้อผิดพลาด"
};

export default function JobList({ jobs, setJobs }: Props) {
  const jobIds = useMemo(() => jobs.map((job) => job.id).join("|"), [jobs]);

  useEffect(() => {
    if (!jobs.length) {
      return;
    }
    let cancelled = false;

    const poll = async () => {
      try {
        const updates = await Promise.all(jobs.map((job) => fetchJob(job.id)));
        if (!cancelled) {
          setJobs(updates);
        }
      } catch (err) {
        console.error("Failed to refresh jobs", err);
      }
    };

    const interval = setInterval(poll, 3000);
    void poll();

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [jobIds, jobs, setJobs]);

  if (!jobs.length) {
    return <p>ยังไม่มีงานประมวลผล</p>;
  }

  return (
    <div className="job-list">
      <h2>สถานะงาน</h2>
      <ul>
        {jobs.map((job) => (
          <li key={job.id}>
            <strong>{job.original_filename ?? job.id}</strong>
            {job.original_filename && (
              <span style={{ marginLeft: "0.5rem", color: "#666" }}>({job.id})</span>
            )}
            <span> – {STATUS_LABELS[job.status] ?? job.status}</span>
            {job.error_message && <p className="error">{job.error_message}</p>}
            {job.text && (
              <pre className="job-text" style={{ whiteSpace: "pre-wrap", marginTop: "0.5rem" }}>
                {job.text}
              </pre>
            )}
            {job.dialect_text && job.dialect_text !== job.text && (
              <details style={{ marginTop: "0.5rem" }}>
                <summary>Dialect mapping</summary>
                <pre style={{ whiteSpace: "pre-wrap", marginTop: "0.25rem" }}>{job.dialect_text}</pre>
              </details>
            )}
            {job.status === "finished" && (
              <div className="downloads">
                <button onClick={() => downloadFile(job.files.txt, `${job.id}.txt`)} disabled={!job.files.txt}>
                  ดาวน์โหลด TXT
                </button>
                <button onClick={() => downloadFile(job.files.srt, `${job.id}.srt`)} disabled={!job.files.srt}>
                  ดาวน์โหลด SRT
                </button>
                <button onClick={() => downloadFile(job.files.vtt, `${job.id}.vtt`)} disabled={!job.files.vtt}>
                  ดาวน์โหลด VTT
                </button>
                <button
                  onClick={() => downloadFile(job.files.jsonl, `${job.id}.jsonl`)}
                  disabled={!job.files.jsonl}
                >
                  ดาวน์โหลด JSONL
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
