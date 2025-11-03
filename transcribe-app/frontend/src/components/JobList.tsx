import { Dispatch, SetStateAction, useEffect } from "react";
import { JobDetail, downloadFile, fetchJob } from "../api/client";

interface Props {
  jobs: JobDetail[];
  setJobs: Dispatch<SetStateAction<JobDetail[]>>;
}

export default function JobList({ jobs, setJobs }: Props) {
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

    const interval = setInterval(poll, 2500);
    void poll();

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [jobs, setJobs]);

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
            {job.original_filename && <span style={{ marginLeft: "0.5rem", color: "#666" }}>({job.id})</span>}
            <span> – {job.status}</span>
            {job.error_message && <p className="error">{job.error_message}</p>}
            {job.text && (
              <pre className="job-text" style={{ whiteSpace: "pre-wrap", marginTop: "0.5rem" }}>
                {job.text}
              </pre>
            )}
            {job.status === "finished" && (
              <div className="downloads">
                <button onClick={() => downloadFile(job.files.txt, `${job.id}.txt`)} disabled={!job.files.txt}>
                  TXT
                </button>
                <button onClick={() => downloadFile(job.files.srt, `${job.id}.srt`)} disabled={!job.files.srt}>
                  SRT
                </button>
                <button onClick={() => downloadFile(job.files.vtt, `${job.id}.vtt`)} disabled={!job.files.vtt}>
                  VTT
                </button>
                <button onClick={() => downloadFile(job.files.jsonl, `${job.id}.jsonl`)} disabled={!job.files.jsonl}>
                  JSONL
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
