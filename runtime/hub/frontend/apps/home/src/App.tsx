import { useState, useEffect, useCallback } from "react";

interface JHData {
  base_url: string;
  xsrf_token: string;
  user: string;
}

interface HomeData {
  server_active: boolean;
  server_url: string;
}

declare global {
  interface Window {
    jhdata?: JHData;
    HOME_DATA?: HomeData;
  }
}

const jhdata: JHData = window.jhdata ?? {
  base_url: "/hub/",
  xsrf_token: "",
  user: "student",
};

const homeData: HomeData = window.HOME_DATA ?? {
  server_active: false,
  server_url: `${jhdata.base_url}spawn`,
};

const baseUrl = jhdata.base_url;

function App() {
  const [serverActive, setServerActive] = useState(homeData.server_active);
  const [stopping, setStopping] = useState(false);
  const [announcement, setAnnouncement] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${baseUrl}static/announcement.txt`)
      .then((resp) => {
        if (!resp.ok) throw new Error("Not found");
        return resp.text();
      })
      .then((data) => {
        if (data?.trim()) setAnnouncement(data.trim());
      })
      .catch(() => {});
  }, []);

  const handleStop = useCallback(
    async (e: React.MouseEvent) => {
      e.preventDefault();
      e.nativeEvent.stopImmediatePropagation();
      if (stopping) return;
      setStopping(true);
      try {
        const resp = await fetch(
          `${baseUrl}api/users/${jhdata.user}/server`,
          {
            method: "DELETE",
            headers: { "X-XSRFToken": jhdata.xsrf_token },
          },
        );
        if (resp.ok || resp.status === 204) {
          setServerActive(false);
        } else if (resp.status === 202) {
          setServerActive(false);
        }
      } catch (err) {
        console.error("Failed to stop server:", err);
      } finally {
        setStopping(false);
      }
    },
    [stopping],
  );

  return (
    <div className="home-page">
      {/* Hero */}
      <section className="home-hero">
        <div className="container">
          <h1>
            Welcome to <span className="accent">AUP Learning Cloud</span>
          </h1>
          <p className="hero-desc">
            Experience next-generation AI acceleration with AMD ROCm. Launch
            GPU-powered Jupyter notebooks for deep learning, computer vision,
            LLMs, and more.
          </p>
        </div>
      </section>

      {/* Launch Bar */}
      <div className="container">
        <div className="launch-bar">
          <div
            className={`lb-icon ${serverActive ? "running" : "stopped"}`}
          >
            <i className="fa fa-server"></i>
          </div>
          <div className="lb-info">
            <div className="lb-title">
              My Server
              {serverActive ? (
                <span className="status-badge running">
                  <span className="status-dot running"></span> Running
                </span>
              ) : (
                <span className="status-badge stopped">
                  <span className="status-dot stopped"></span> Stopped
                </span>
              )}
            </div>
            <div className="lb-desc">
              {stopping
                ? "Stopping your server…"
                : serverActive
                  ? 'Your server is running \u2014 click "My Server" to open JupyterLab'
                  : "Choose a course and launch your Jupyter environment"}
            </div>
          </div>
          <div className="lb-actions">
            {serverActive ? (
              <>
                <a
                  id="stop"
                  role="button"
                  className="btn-home-sm danger"
                  onClick={handleStop}
                >
                  <i className={`fa ${stopping ? "fa-spinner fa-spin" : "fa-stop"}`}></i>{" "}
                  {stopping ? "Stopping…" : "Stop My Server"}
                </a>
                <a
                  id="start"
                  role="button"
                  className="btn-launch"
                  href={homeData.server_url}
                >
                  <i className="fa fa-external-link"></i> My Server
                </a>
              </>
            ) : (
              <a
                id="start"
                role="button"
                className="btn-launch"
                href={`${baseUrl}spawn`}
              >
                <i className="fa fa-play"></i> Start My Server
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Quick Start */}
      <div className="container">
        <section className="home-section">
          <div className="home-section-header">
            <h2>Quick Start</h2>
          </div>
          <div className="qs-grid">
            <div className="qs-card">
              <div className="qs-num">1</div>
              <h3>Choose a Course</h3>
              <p>
                Select from pre-configured environments for CV, Deep Learning,
                LLMs, or Physics Simulation.
              </p>
            </div>
            <div className="qs-card">
              <div className="qs-num">2</div>
              <h3>Launch Your Server</h3>
              <p>
                Click &ldquo;Start My Server&rdquo; to spin up a Jupyter
                environment with GPU/NPU acceleration.
              </p>
            </div>
            <div className="qs-card">
              <div className="qs-num">3</div>
              <h3>Start Learning</h3>
              <p>
                Open notebooks, run experiments, and explore AMD ROCm-powered AI
                workflows.
              </p>
            </div>
          </div>
        </section>
      </div>

      {/* Available Courses */}
      <div className="container">
        <section className="home-section" style={{ paddingTop: 0 }}>
          <div className="home-section-header">
            <h2>Available Courses</h2>
            <a href={`${baseUrl}spawn`}>
              View all in Spawner{" "}
              <i className="fa fa-arrow-right" style={{ fontSize: "0.7rem" }}></i>
            </a>
          </div>
          <div className="courses-grid">
            <a className="course-card" href={`${baseUrl}spawn`}>
              <div className="course-icon icon-cv">CV</div>
              <h3>Computer Vision</h3>
              <p>
                Image classification, object detection &amp; segmentation with
                AMD GPUs.
              </p>
              <span className="course-tag tag-gpu">GPU</span>
            </a>
            <a className="course-card" href={`${baseUrl}spawn`}>
              <div className="course-icon icon-dl">DL</div>
              <h3>Deep Learning</h3>
              <p>
                Neural networks, training pipelines &amp; optimization on ROCm.
              </p>
              <span className="course-tag tag-gpu">GPU</span>
            </a>
            <a className="course-card" href={`${baseUrl}spawn`}>
              <div className="course-icon icon-llm">LLM</div>
              <h3>Large Language Models</h3>
              <p>
                Transformer fine-tuning &amp; inference with AMD Instinct
                accelerators.
              </p>
              <span className="course-tag tag-gpu">GPU</span>
            </a>
            <a className="course-card" href={`${baseUrl}spawn`}>
              <div className="course-icon icon-phy">PS</div>
              <h3>Physics Simulation</h3>
              <p>Scientific computing &amp; physics-based simulations.</p>
              <span className="course-tag tag-cpu">CPU</span>
            </a>
          </div>
        </section>
      </div>

      {/* Docs + News */}
      <div className="container">
        <section className="home-section" style={{ paddingTop: 0 }}>
          <div className="home-two-col">
            <div>
              <div className="home-section-header">
                <h2>Documentation</h2>
              </div>
              <div className="doc-list">
                <a
                  className="doc-item"
                  href="https://rocm.docs.amd.com/"
                  target="_blank"
                  rel="noopener"
                >
                  <div
                    className="doc-icon"
                    style={{ background: "#fce8e6", color: "#d93025" }}
                  >
                    <i className="fa fa-book"></i>
                  </div>
                  <div className="doc-text">
                    <h4>AMD ROCm Documentation</h4>
                    <p>Official ROCm platform docs &amp; API references</p>
                  </div>
                </a>
                <a
                  className="doc-item"
                  href="https://amdresearch.github.io/aup-learning-cloud/"
                  target="_blank"
                  rel="noopener"
                >
                  <div
                    className="doc-icon"
                    style={{ background: "#e8f0fe", color: "#1a73e8" }}
                  >
                    <i className="fa fa-laptop"></i>
                  </div>
                  <div className="doc-text">
                    <h4>AUP Learning Cloud User Guide</h4>
                    <p>Notebooks, terminals &amp; extensions</p>
                  </div>
                </a>
                <a
                  className="doc-item"
                  href="https://amdresearch.github.io/aup-learning-cloud/installation/single-node.html"
                  target="_blank"
                  rel="noopener"
                >
                  <div
                    className="doc-icon"
                    style={{ background: "#f3e8fd", color: "#9334e6" }}
                  >
                    <i className="fa fa-rocket"></i>
                  </div>
                  <div className="doc-text">
                    <h4>Platform Getting Started</h4>
                    <p>First-time user guide fo AUP Learning Cloud setup</p>
                  </div>
                </a>
                <a
                  className="doc-item"
                  href="https://github.com/AMDResearch/aup-learning-cloud"
                  target="_blank"
                  rel="noopener"
                >
                  <div
                    className="doc-icon"
                    style={{ background: "#e6f4ea", color: "#1e8e3e" }}
                  >
                    <i className="fa fa-code-fork"></i>
                  </div>
                  <div className="doc-text">
                    <h4>AUP Learning Cloud GitHub Repository</h4>
                    <p>Clone &amp; launch your own AUP Learning Cloud </p>
                  </div>
                </a>
              </div>
            </div>
            <div>
              <div className="home-section-header">
                <h2>News &amp; Updates</h2>
              </div>
              <div className="news-list">
                {announcement && (
                  <div className="news-card">
                    <div className="news-meta">Announcement</div>
                    <h4>Platform Announcement</h4>
                    <p>{announcement}</p>
                  </div>
                )}
                <div className="news-card">
                  <div className="news-meta">Platform</div>
                  <h4>Welcome to AUP Learning Cloud</h4>
                  <p>
                    Get started with GPU-accelerated Jupyter notebooks powered
                    by AMD ROCm technology.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>

      {/* Footer */}
      <div className="home-footer">
        <div className="container">
          &copy; 2025 Advanced Micro Devices, Inc. All rights reserved. &middot;
          AUP Learning Cloud
        </div>
      </div>
    </div>
  );
}

export default App;
