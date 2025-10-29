import { useEffect } from "react";
import { JobResult, JobStatus, downloadResult, fetchJob, fetchResult } from "../api/client";

interface Props {
  jobs: JobStatus[];
  setJobs: (jobs: JobStatus[]) => void;
  onResult: (result: JobResult) => void;
}

export default function JobList({ jobs, setJobs, onResult }: Props) {
  useEffect(() => {
    const interval = setInterval(async () => {
      const updates: JobStatus[] = [];
      for (const job of jobs) {
        if (job.status === "finished") {
          updates.push(job);
          continue;
        }
        const next = await fetchJob(job.job_id);
        updates.push(next);
        if (next.status === "finished") {
          const result = await fetchResult(job.job_id);
          onResult(result);
        }
      }
      if (updates.length) {
        setJobs(updates);
      }
    }, 2500);
    return () => clearInterval(interval);
  }, [jobs, onResult, setJobs]);

  if (!jobs.length) {
    return <p>ยังไม่มีงานประมวลผล</p>;
  }

  return (
    <div className="job-list">
      <h2>สถานะงาน</h2>
      <ul>
        {jobs.map((job) => (
          <li key={job.job_id}>
            <strong>{job.job_id}</strong> – {job.status}
            {job.status === "finished" && (
              <>
                <button onClick={() => downloadResult(job.job_id, "txt")}>TXT</button>
                <button onClick={() => downloadResult(job.job_id, "srt")}>SRT</button>
                <button onClick={() => downloadResult(job.job_id, "vtt")}>VTT</button>
                <button onClick={() => downloadResult(job.job_id, "jsonl")}>JSONL</button>
              </>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
