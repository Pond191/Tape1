import { useState } from "react";

import Upload from "./components/Upload";
import JobList from "./components/JobList";
import { JobDetail, JobSummary } from "./api/client";

export default function App() {
  const [jobs, setJobs] = useState<JobDetail[]>([]);

  const handleJobCreated = (job: JobSummary) => {
    const initialJob: JobDetail = {
      id: job.id,
      status: job.status,
      text: null,
      dialect_text: null,
      error_message: null,
      original_filename: null,
      files: { txt: null, srt: null, vtt: null, jsonl: null }
    };
    setJobs((current) => [...current, initialJob]);
  };

  return (
    <div className="app">
      <header>
        <h1>Dialect Transcribe</h1>
        <p>ถอดเทปไทย/อีสาน/เหนือ/ใต้ พร้อมโค้ดสวิตช์</p>
      </header>
      <main>
        <Upload onJobCreated={handleJobCreated} />
        <JobList jobs={jobs} setJobs={setJobs} />
      </main>
    </div>
  );
}
