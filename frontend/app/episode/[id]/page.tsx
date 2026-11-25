"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Clapperboard,
  Sparkles,
  RefreshCw,
  Play,
  Film,
  Camera,
  MessageSquare,
  ShieldCheck,
  Save,
  CheckCircle2,
  AlertTriangle,
  MoveHorizontal,
  Wand2,
  Video,
  Check,
  Zap,
  Sliders,
  RotateCcw,
  Scissors,
  Download,
  Share2,
  Music,
  Subtitles,
  Palette
} from "lucide-react";
import { API_BASE } from "@/lib/api";

interface ShotItem {
  id: number;
  shot_number: number;
  beat_type: string;
  duration_sec: number;
  camera_angle: string;
  camera_movement: string;
  spatial_blocking: string;
  props_continuity?: string | null;
  dialogue: string | null;
  compiled_prompt: string;
  pass1_status: string;
  pass1_video_url: string | null;
  pass2_status: string;
  pass2_video_url: string | null;
  previous_interaction_id: string | null;
  safety_retry_count: number;
  last_error_message: string | null;
  selected_pass: string;
  final_video_url: string | null;
}

interface EpisodeData {
  id: number;
  series_id: number;
  episode_number: number;
  title: string;
  premise: string;
  outline_summary?: string | null;
  continuity_notes?: string | null;
  status: string;
  final_video_url: string | null;
  shots: ShotItem[];
}

interface CostEstimate {
  shot_count: number;
  duration_total_sec: number;
  pass1_cost_usd: number;
  pass1_credits: number;
  pass2_cost_usd: number;
  pass2_credits: number;
  full_pipeline_usd: number;
  full_pipeline_credits: number;
}

interface AssemblyMetadata {
  duration_sec: number;
  resolution: string;
  subtitles_burned: number;
  bgm_level_db: number;
  file_size_mb: number;
}

export default function EpisodeProductionDesk() {
  const params = useParams();
  const episodeId = params.id as string;

  const [episode, setEpisode] = useState<EpisodeData | null>(null);
  const [costEstimate, setCostEstimate] = useState<CostEstimate | null>(null);
  const [loading, setLoading] = useState(true);
  const [directing, setDirecting] = useState(false);

  // Batch rendering states
  const [renderingPass1, setRenderingPass1] = useState(false);
  const [renderingPass2, setRenderingPass2] = useState(false);
  const [renderingShotId, setRenderingShotId] = useState<number | null>(null);

  // Assembly pipeline state
  const [assembling, setAssembling] = useState(false);
  const [assemblyMeta, setAssemblyMeta] = useState<AssemblyMetadata | null>(null);

  // Targeted fix state
  const [targetedFixShotId, setTargetedFixShotId] = useState<number | null>(null);
  const [targetedFixText, setTargetedFixText] = useState("");
  const [applyingFix, setApplyingFix] = useState(false);

  // Prompt edit state
  const [editingShotId, setEditingShotId] = useState<number | null>(null);
  const [editPrompt, setEditPrompt] = useState("");
  const [editDialogue, setEditDialogue] = useState("");
  const [savingShot, setSavingShot] = useState(false);

  // Confirmation modals
  const [showPass1Modal, setShowPass1Modal] = useState(false);
  const [showPass2Modal, setShowPass2Modal] = useState(false);
  const [toast, setToast] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const showToast = (type: "success" | "error", text: string) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), 5000);
  };

  const fetchEpisode = async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      const [resEp, resCost] = await Promise.all([
        fetch(`${API_BASE}/api/episodes/${episodeId}`),
        fetch(`${API_BASE}/api/shots/estimate?shot_count=4`)
      ]);

      if (resEp.ok) {
        const data = await resEp.json();
        setEpisode(data);
        const anyProcessing = data.shots?.some(
          (s: ShotItem) => s.pass1_status === "processing" || s.pass2_status === "processing"
        );
        if (!anyProcessing) {
          setRenderingPass1(false);
          setRenderingPass2(false);
        }
      }
      if (resCost.ok) {
        const cData = await resCost.json();
        setCostEstimate(cData);
      }
    } catch (err) {
      console.error("Error fetching episode:", err);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  const dispatchBalanceUpdate = () => {
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("creditBalanceUpdated"));
    }
  };

  useEffect(() => {
    if (episodeId) {
      fetchEpisode();
    }
  }, [episodeId]);

  // Live async polling while any shot is processing in the background
  useEffect(() => {
    const isAnyProcessing =
      renderingPass1 ||
      renderingPass2 ||
      episode?.status === "rendering" ||
      episode?.shots?.some((s) => s.pass1_status === "processing" || s.pass2_status === "processing");

    if (!isAnyProcessing) return;

    const timer = setInterval(() => {
      fetchEpisode(true);
      dispatchBalanceUpdate();
    }, 2500);

    return () => clearInterval(timer);
  }, [renderingPass1, renderingPass2, episode?.status, episode?.shots]);

  const handleAutoDirect = async () => {
    try {
      setDirecting(true);
      const res = await fetch(`${API_BASE}/api/episodes/${episodeId}/auto-direct`, {
        method: "POST"
      });
      if (res.ok) {
        showToast("success", "4-Beat Micro-Drama script & compiled prompts generated.");
        await fetchEpisode(true);
      } else {
        showToast("error", "Failed to auto-direct episode.");
      }
    } catch (e) {
      console.error("Director generation failed:", e);
      showToast("error", "Network error while directing script.");
    } finally {
      setDirecting(false);
    }
  };

  const handleBatchPass1 = async () => {
    setShowPass1Modal(false);
    try {
      setRenderingPass1(true);
      const res = await fetch(`${API_BASE}/api/episodes/${episodeId}/render-pass1?async_mode=true`, {
        method: "POST"
      });
      if (res.ok) {
        showToast("success", "Pass 1 (360p Draft) batch queued. Shots will appear live as they complete.");
        await fetchEpisode(true);
      } else if (res.status === 402) {
        setRenderingPass1(false);
        showToast("error", "Insufficient credits! Click your credit balance in the Navbar to top up.");
      } else {
        setRenderingPass1(false);
        showToast("error", "Failed to start Pass 1 batch.");
      }
    } catch (e) {
      console.error("Pass 1 batch failed:", e);
      setRenderingPass1(false);
    }
  };

  const handleBatchPass2 = async () => {
    setShowPass2Modal(false);
    try {
      setRenderingPass2(true);
      const res = await fetch(`${API_BASE}/api/episodes/${episodeId}/render-pass2?async_mode=true`, {
        method: "POST"
      });
      if (res.ok) {
        showToast("success", "Pass 2 (720p Final) batch queued. Master clips will appear live.");
        await fetchEpisode(true);
      } else if (res.status === 402) {
        setRenderingPass2(false);
        showToast("error", "Insufficient credits! Click your credit balance in the Navbar to top up.");
      } else {
        setRenderingPass2(false);
        showToast("error", "Failed to start Pass 2 batch.");
      }
    } catch (e) {
      console.error("Pass 2 batch failed:", e);
      setRenderingPass2(false);
    }
  };

  const handleAssembleEpisode = async () => {
    try {
      setAssembling(true);
      const res = await fetch(`${API_BASE}/api/episodes/${episodeId}/assemble`, {
        method: "POST"
      });
      if (res.ok) {
        const data = await res.json();
        setAssemblyMeta({
          duration_sec: data.duration_sec,
          resolution: data.resolution,
          subtitles_burned: data.subtitles_burned,
          bgm_level_db: data.bgm_level_db,
          file_size_mb: data.file_size_mb
        });
        showToast("success", `Master 9:16 MP4 assembled (${data.file_size_mb} MB, ${data.subtitles_burned} subtitles burned).`);
        await fetchEpisode(true);
      } else {
        const err = await res.json();
        showToast("error", `Assembly failed: ${err.detail || "Unknown error"}`);
      }
    } catch (e) {
      console.error("Assembly failed:", e);
      showToast("error", "Network error during FFmpeg assembly.");
    } finally {
      setAssembling(false);
    }
  };

  const handleRenderSingleShot = async (shotId: number, passNum: number) => {
    try {
      setRenderingShotId(shotId);
      const res = await fetch(`${API_BASE}/api/shots/${shotId}/render`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pass_number: passNum })
      });
      if (res.ok) {
        dispatchBalanceUpdate();
        await fetchEpisode();
      } else if (res.status === 402) {
        alert("Insufficient credit balance!");
      }
    } catch (e) {
      console.error("Single shot render error:", e);
    } finally {
      setRenderingShotId(null);
    }
  };

  const handleApplyTargetedFix = async (shotId: number) => {
    if (!targetedFixText.trim()) return;
    try {
      setApplyingFix(true);
      const res = await fetch(`${API_BASE}/api/shots/${shotId}/edit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ edit_instruction: targetedFixText })
      });
      if (res.ok) {
        dispatchBalanceUpdate();
        setTargetedFixShotId(null);
        setTargetedFixText("");
        await fetchEpisode();
      }
    } catch (e) {
      console.error("Targeted fix failed:", e);
    } finally {
      setApplyingFix(false);
    }
  };

  const handleReframeSafety = async (shotId: number) => {
    try {
      setRenderingShotId(shotId);
      const res = await fetch(`${API_BASE}/api/shots/${shotId}/reframe-safety`, {
        method: "POST"
      });
      if (res.ok) {
        dispatchBalanceUpdate();
        await fetchEpisode();
      }
    } catch (e) {
      console.error("Safety reframe failed:", e);
    } finally {
      setRenderingShotId(null);
    }
  };

  const startEditShot = (shot: ShotItem) => {
    setEditingShotId(shot.id);
    setEditPrompt(shot.compiled_prompt);
    setEditDialogue(shot.dialogue || "");
  };

  const handleSaveShot = async (shotId: number) => {
    try {
      setSavingShot(true);
      const res = await fetch(`${API_BASE}/api/shots/${shotId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          compiled_prompt: editPrompt,
          dialogue: editDialogue
        })
      });
      if (res.ok) {
        setEditingShotId(null);
        await fetchEpisode();
      }
    } catch (e) {
      console.error("Failed to save shot:", e);
    } finally {
      setSavingShot(false);
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center text-slate-400 space-y-3">
        <RefreshCw className="w-8 h-8 animate-spin mx-auto text-amber-400" />
        <p className="font-mono text-sm">Opening Studio Production Desk...</p>
      </div>
    );
  }

  if (!episode) {
    return (
      <div className="py-12 text-center text-slate-400">
        <p>Episode not found.</p>
        <Link href="/" className="text-amber-400 text-xs underline mt-2 inline-block">
          Return to Dashboard
        </Link>
      </div>
    );
  }

  const hasShots = episode.shots && episode.shots.length === 4;
  const pass1ReadyCount = episode.shots?.filter((s) => s.pass1_status === "completed").length || 0;
  const pass2ReadyCount = episode.shots?.filter((s) => s.pass2_status === "completed").length || 0;
  const hasRenderedClips = pass1ReadyCount > 0 || pass2ReadyCount > 0;

  return (
    <div className="space-y-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <Link
          href={`/series/${episode.series_id}`}
          className="inline-flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Visual Bible</span>
        </Link>
        <div className="flex items-center gap-3">
          <span className="px-2.5 py-1 rounded-full text-xs font-mono font-semibold bg-amber-500/10 border border-amber-500/20 text-amber-300">
            Episode #{episode.episode_number} &bull; {episode.status.toUpperCase()}
          </span>
          <span className="px-2.5 py-1 rounded-full text-xs font-mono font-semibold bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
            60s Vertical 9:16
          </span>
        </div>
      </div>

      {/* Production Control Room Card */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 space-y-5">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs font-mono font-semibold">
              <Clapperboard className="w-3.5 h-3.5 text-amber-400" />
              <span>4-Beat Micro-Drama Production</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              {episode.title}
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
              {episode.premise}
            </p>
          </div>

          {/* Action Toolbar */}
          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <button
              onClick={handleAutoDirect}
              disabled={directing || renderingPass1 || renderingPass2 || assembling}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-semibold transition-all cursor-pointer disabled:opacity-50"
            >
              {directing ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin text-amber-400" />
                  <span>Directing...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 text-amber-400" />
                  <span>{hasShots ? "Re-Direct Script" : "Auto-Direct 4x15s Script"}</span>
                </>
              )}
            </button>

            {hasShots && (
              <>
                <button
                  onClick={() => setShowPass1Modal(true)}
                  disabled={renderingPass1 || renderingPass2 || assembling}
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/40 text-amber-300 font-bold text-xs transition-all cursor-pointer disabled:opacity-50"
                >
                  {renderingPass1 ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Rendering 360p Draft ({pass1ReadyCount}/4)...</span>
                    </>
                  ) : (
                    <>
                      <Zap className="w-4 h-4 text-amber-400" />
                      <span>Pass 1: 360p Draft ($1.40)</span>
                    </>
                  )}
                </button>

                <button
                  onClick={() => setShowPass2Modal(true)}
                  disabled={renderingPass1 || renderingPass2 || assembling}
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold text-xs shadow-lg shadow-amber-500/20 transition-all cursor-pointer disabled:opacity-50"
                >
                  {renderingPass2 ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Rendering 720p Final ({pass2ReadyCount}/4)...</span>
                    </>
                  ) : (
                    <>
                      <Video className="w-4 h-4" />
                      <span>Pass 2: 720p Final ($4.16)</span>
                    </>
                  )}
                </button>

                {/* Auto-Assembly FFmpeg Button */}
                <button
                  onClick={handleAssembleEpisode}
                  disabled={assembling || renderingPass1 || renderingPass2}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-extrabold text-xs shadow-lg shadow-emerald-500/20 transition-all cursor-pointer disabled:opacity-50"
                >
                  {assembling ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Assembling FFmpeg Pipeline...</span>
                    </>
                  ) : (
                    <>
                      <Scissors className="w-4 h-4" />
                      <span>Auto-Assemble 60s Vertical MP4</span>
                    </>
                  )}
                </button>
              </>
            )}
          </div>
        </div>

        {/* Cost & Render Status Banner */}
        {costEstimate && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
            <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1">
              <span className="text-[10px] text-slate-400 font-mono uppercase">Timeline</span>
              <p className="text-sm font-bold text-white">4 x 15s + 1.5s Outro</p>
            </div>
            <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-slate-400 font-mono uppercase">Pass 1 (360p Draft)</span>
                <span className="text-[10px] text-amber-400 font-mono font-bold">{pass1ReadyCount}/4 Ready</span>
              </div>
              <p className="text-sm font-bold text-amber-400">
                ${costEstimate.pass1_cost_usd.toFixed(2)}{" "}
                <span className="text-[10px] font-normal text-slate-400 font-mono">({costEstimate.pass1_credits} credits)</span>
              </p>
            </div>
            <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-slate-400 font-mono uppercase">Pass 2 (720p Final)</span>
                <span className="text-[10px] text-emerald-400 font-mono font-bold">{pass2ReadyCount}/4 Ready</span>
              </div>
              <p className="text-sm font-bold text-emerald-400">
                ${costEstimate.pass2_cost_usd.toFixed(2)}{" "}
                <span className="text-[10px] font-normal text-slate-400 font-mono">({costEstimate.pass2_credits} credits)</span>
              </p>
            </div>
            <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1">
              <span className="text-[10px] text-slate-400 font-mono uppercase">Status</span>
              <p className="text-sm font-bold text-white capitalize">{episode.status.replace("_", " ")}</p>
            </div>
          </div>
        )}

        {/* Toast Notification Banner */}
        {toast && (
          <div
            className={`p-3 rounded-xl border text-xs font-medium flex items-center justify-between ${
              toast.type === "success"
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                : "bg-rose-500/10 border-rose-500/30 text-rose-300"
            }`}
          >
            <span>{toast.text}</span>
            <button onClick={() => setToast(null)} className="text-xs opacity-70 hover:opacity-100">
              ✕
            </button>
          </div>
        )}

        {/* Continuity & Director Notes */}
        {episode.continuity_notes && (
          <div className="p-3.5 rounded-xl bg-amber-500/5 border border-amber-500/20 flex items-start gap-3">
            <ShieldCheck className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
            <div className="text-xs space-y-1">
              <span className="font-semibold text-amber-300 font-mono text-[11px] uppercase">
                180° Continuity & Props Lock:
              </span>
              <p className="text-slate-300 text-[11px] leading-relaxed">{episode.continuity_notes}</p>
            </div>
          </div>
        )}
      </div>

      {/* Final Assembled Master Video Preview */}
      {episode.final_video_url && (
        <div className="rounded-2xl bg-gradient-to-r from-emerald-950/30 via-slate-900 to-slate-900 border border-emerald-500/40 p-6 space-y-6 shadow-2xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
            <div>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-mono text-xs font-semibold">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>FFmpeg Master Assembly Complete</span>
              </div>
              <h2 className="text-xl font-bold text-white mt-1">Ready-to-Post 60s Vertical Micro-Drama</h2>
              <p className="text-xs text-slate-400">
                Continuous 4-shot concatenation, 0.2s crossfades, -22dB suspense score, burned centered captions, and 1.5s cliffhanger card.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <a
                href={`${API_BASE}${episode.final_video_url}`}
                download={`microdrama_ep${episode.episode_number}.mp4`}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs shadow-lg shadow-emerald-500/20 transition-all cursor-pointer"
              >
                <Download className="w-4 h-4" />
                <span>Download Master MP4</span>
              </a>
              <button
                onClick={handleAssembleEpisode}
                disabled={assembling}
                className="inline-flex items-center gap-1.5 px-3 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition-all cursor-pointer"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${assembling ? "animate-spin text-amber-400" : ""}`} />
                <span>Re-Assemble</span>
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
            {/* 9:16 Video Master Player */}
            <div className="md:col-span-5 flex justify-center">
              <div className="relative aspect-[9/16] w-full max-w-[280px] rounded-2xl bg-black border-2 border-emerald-500/40 overflow-hidden shadow-2xl">
                <video
                  key={episode.final_video_url}
                  src={`${API_BASE}${episode.final_video_url}`}
                  controls
                  playsInline
                  autoPlay={false}
                  className="w-full h-full object-cover"
                />
              </div>
            </div>

            {/* Technical Specs Breakdown */}
            <div className="md:col-span-7 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-1">
                  <div className="flex items-center gap-2 text-emerald-400 font-semibold font-mono">
                    <Scissors className="w-4 h-4" />
                    <span>Timeline & Crossfades</span>
                  </div>
                  <p className="text-slate-300">4 x 15s clips with 0.2s smooth audio crossfades + 1.5s cliffhanger card (~61.5s).</p>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-1">
                  <div className="flex items-center gap-2 text-amber-400 font-semibold font-mono">
                    <Music className="w-4 h-4" />
                    <span>Atmospheric BGM</span>
                  </div>
                  <p className="text-slate-300">Continuous royalty-free suspense score auto-ducked to exactly -22dB.</p>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-1">
                  <div className="flex items-center gap-2 text-sky-400 font-semibold font-mono">
                    <Subtitles className="w-4 h-4" />
                    <span>Burned Captions</span>
                  </div>
                  <p className="text-slate-300">Centered-bottom 9:16 dialogue subtitles with high-contrast semi-transparent backing.</p>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-1">
                  <div className="flex items-center gap-2 text-purple-400 font-semibold font-mono">
                    <Palette className="w-4 h-4" />
                    <span>Cinematic Color Grade</span>
                  </div>
                  <p className="text-slate-300">Unified contrast curve (eq 1.12) & saturation (1.18) matching series lighting.</p>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-slate-950/90 border border-slate-800 flex items-center justify-between text-xs font-mono text-slate-400">
                <span>Output Format: H.264 / AAC 128k</span>
                <span className="text-emerald-400">Ready for TikTok &bull; Reels &bull; Shorts</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 4 Shots Timeline */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Film className="w-5 h-5 text-amber-400" />
            <span>Episode Shots Timeline (4 x 15s)</span>
          </h2>
          <span className="text-xs text-slate-400 font-mono">
            {episode.shots?.length || 0}/4 Shots Directed
          </span>
        </div>

        {(!episode.shots || episode.shots.length === 0) ? (
          <div className="p-12 text-center border border-dashed border-slate-800 rounded-2xl bg-slate-900/30 space-y-4">
            <Clapperboard className="w-10 h-10 mx-auto text-amber-400 opacity-60" />
            <div className="space-y-1">
              <h3 className="font-bold text-white text-base">No Screenplay Generated Yet</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Click "Auto-Direct 4x15s Script" above to generate the structured 4-beat micro-drama outline and compiled Omni prompts.
              </p>
            </div>
            <button
              onClick={handleAutoDirect}
              disabled={directing}
              className="px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs"
            >
              Generate 4-Beat Script Now
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {episode.shots.map((shot) => {
              const isEditing = editingShotId === shot.id;
              const isFixing = targetedFixShotId === shot.id;
              const isRenderingThis = renderingShotId === shot.id;
              const hasVideo = shot.final_video_url || shot.pass1_video_url || shot.pass2_video_url;
              const activeVideoUrl = shot.final_video_url || shot.pass2_video_url || shot.pass1_video_url;
              const hasSafetyError = shot.last_error_message?.includes("Safety Policy Violation");

              return (
                <div
                  key={shot.id}
                  className="rounded-2xl bg-slate-900/90 border border-slate-800 hover:border-slate-700 p-5 space-y-4 flex flex-col justify-between transition-all shadow-md"
                >
                  <div className="space-y-3">
                    {/* Header: Beat & Camera Info */}
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
                      <div className="flex items-center gap-2">
                        <span className="w-6 h-6 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center font-mono text-xs font-bold text-amber-400">
                          {shot.shot_number}
                        </span>
                        <span className="font-bold text-sm text-white">{shot.beat_type}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px] font-mono border border-slate-700">
                          {shot.camera_angle}
                        </span>
                        <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[10px] font-mono border border-emerald-500/20">
                          15s
                        </span>
                      </div>
                    </div>

                    {/* Prominent People Safety Filter Alert */}
                    {hasSafetyError && (
                      <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 space-y-2">
                        <div className="flex items-center gap-2 text-xs font-semibold text-rose-300">
                          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                          <span>Prominent People Safety Flag Detected</span>
                        </div>
                        <p className="text-[11px] text-rose-200/80 leading-relaxed">
                          {shot.last_error_message}. No credits were deducted.
                        </p>
                        <button
                          onClick={() => handleReframeSafety(shot.id)}
                          disabled={isRenderingThis}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500 hover:bg-rose-400 text-slate-950 font-bold text-xs transition-all cursor-pointer"
                        >
                          <RotateCcw className="w-3.5 h-3.5" />
                          <span>Reframe Safely & Retry (Over-The-Shoulder)</span>
                        </button>
                      </div>
                    )}

                    {/* Inline Video Player (9:16 vertical) or Placeholder */}
                    <div className="relative aspect-[9/16] w-full max-w-[240px] mx-auto rounded-xl bg-black border border-slate-800 overflow-hidden flex items-center justify-center shadow-lg">
                      {isRenderingThis ? (
                        <div className="p-4 text-center space-y-2">
                          <RefreshCw className="w-8 h-8 animate-spin text-amber-400 mx-auto" />
                          <p className="text-xs font-mono text-amber-300">Rendering Video...</p>
                        </div>
                      ) : activeVideoUrl ? (
                        <video
                          src={`${API_BASE}${activeVideoUrl}`}
                          controls
                          playsInline
                          preload="metadata"
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="p-4 text-center space-y-2 text-slate-500">
                          <Play className="w-8 h-8 opacity-40 mx-auto" />
                          <span className="block text-[11px] font-mono">Unrendered (15s)</span>
                          <button
                            onClick={() => handleRenderSingleShot(shot.id, 1)}
                            className="mt-2 px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-semibold border border-slate-700 transition-all cursor-pointer"
                          >
                            Render 360p Draft
                          </button>
                        </div>
                      )}

                      {/* Video Pass Badge */}
                      {activeVideoUrl && (
                        <div className="absolute top-2 right-2 px-2 py-0.5 rounded bg-black/80 backdrop-blur-sm border border-slate-700 text-[10px] font-mono font-bold text-amber-400">
                          {shot.pass2_status === "completed" ? "720p Final" : "360p Draft"}
                        </div>
                      )}
                    </div>

                    {/* 180° Spatial Blocking & Movement */}
                    <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-1">
                      <div className="flex items-center gap-1.5 text-[10px] font-mono text-amber-400 uppercase tracking-wider">
                        <MoveHorizontal className="w-3 h-3" />
                        <span>180° Spatial Blocking</span>
                      </div>
                      <p className="text-xs text-slate-300 font-medium">{shot.spatial_blocking}</p>
                      <p className="text-[11px] text-slate-400 font-mono italic">
                        Camera Movement: {shot.camera_movement}
                      </p>
                    </div>

                    {/* Dialogue Transcript */}
                    {shot.dialogue && (
                      <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1.5">
                        <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-400 uppercase tracking-wider">
                          <MessageSquare className="w-3 h-3 text-amber-400" />
                          <span>Dialogue & Timestamps</span>
                        </div>
                        {isEditing ? (
                          <textarea
                            rows={3}
                            value={editDialogue}
                            onChange={(e) => setEditDialogue(e.target.value)}
                            className="w-full px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-200 font-mono focus:outline-none focus:border-amber-500"
                          />
                        ) : (
                          <pre className="text-xs text-slate-300 whitespace-pre-wrap font-sans leading-relaxed">
                            {shot.dialogue}
                          </pre>
                        )}
                      </div>
                    )}

                    {/* Compiled Omni Prompt */}
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1">
                          <Camera className="w-3 h-3 text-amber-400" />
                          <span>Compiled Gemini Omni Prompt:</span>
                        </span>
                        {!isEditing && (
                          <button
                            onClick={() => startEditShot(shot)}
                            className="text-[10px] text-amber-400 hover:text-amber-300 underline font-mono"
                          >
                            Edit Prompt
                          </button>
                        )}
                      </div>

                      {isEditing ? (
                        <div className="space-y-2">
                          <textarea
                            rows={4}
                            value={editPrompt}
                            onChange={(e) => setEditPrompt(e.target.value)}
                            className="w-full p-2.5 rounded-xl bg-slate-950 border border-amber-500/50 text-xs text-slate-200 font-mono leading-relaxed focus:outline-none"
                          />
                          <div className="flex justify-end gap-2">
                            <button
                              onClick={() => setEditingShotId(null)}
                              className="px-3 py-1 rounded-lg bg-slate-800 text-slate-300 text-xs"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={() => handleSaveShot(shot.id)}
                              disabled={savingShot}
                              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-amber-500 text-slate-950 font-bold text-xs"
                            >
                              <Save className="w-3 h-3" />
                              <span>{savingShot ? "Saving..." : "Save Prompt"}</span>
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/80 text-[11px] font-mono text-slate-300 leading-relaxed max-h-32 overflow-y-auto">
                          {shot.compiled_prompt}
                        </div>
                      )}
                    </div>

                    {/* Targeted Fix (Multi-turn Edit via previous_interaction_id) */}
                    {shot.pass1_status === "completed" && (
                      <div className="pt-2">
                        {isFixing ? (
                          <div className="p-3 rounded-xl bg-slate-950 border border-amber-500/30 space-y-2">
                            <div className="flex items-center justify-between text-xs font-semibold text-amber-300">
                              <span className="flex items-center gap-1">
                                <Wand2 className="w-3.5 h-3.5 text-amber-400" />
                                <span>Targeted Fix (Multi-Turn Edit)</span>
                              </span>
                              <span className="text-[10px] text-slate-400 font-mono">
                                Uses interaction #{shot.previous_interaction_id?.slice(0, 14)}...
                              </span>
                            </div>
                            <input
                              type="text"
                              placeholder="e.g. Adjust lip-sync, change drink to champagne, soften backlight..."
                              value={targetedFixText}
                              onChange={(e) => setTargetedFixText(e.target.value)}
                              className="w-full px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-amber-500"
                            />
                            <div className="flex justify-end gap-2 pt-1">
                              <button
                                onClick={() => setTargetedFixShotId(null)}
                                className="px-3 py-1 rounded-lg bg-slate-800 text-slate-400 text-xs"
                              >
                                Cancel
                              </button>
                              <button
                                onClick={() => handleApplyTargetedFix(shot.id)}
                                disabled={applyingFix || !targetedFixText.trim()}
                                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-amber-500 text-slate-950 font-bold text-xs disabled:opacity-50"
                              >
                                {applyingFix ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
                                <span>Apply Fix (35 credits)</span>
                              </button>
                            </div>
                          </div>
                        ) : (
                          <button
                            onClick={() => {
                              setTargetedFixShotId(shot.id);
                              setTargetedFixText("");
                            }}
                            className="inline-flex items-center gap-1.5 text-xs text-amber-400 hover:text-amber-300 font-medium"
                          >
                            <Wand2 className="w-3.5 h-3.5" />
                            <span>Request Targeted Fix / Multi-Turn Edit</span>
                          </button>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Card Footer: Status & Actions */}
                  <div className="pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-2 text-xs">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-mono text-slate-400">P1:</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase border ${
                        shot.pass1_status === "completed"
                          ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                          : "bg-slate-800 text-slate-400 border-slate-700"
                      }`}>
                        {shot.pass1_status}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-mono text-slate-400">P2:</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase border ${
                        shot.pass2_status === "completed"
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                          : "bg-slate-800 text-slate-400 border-slate-700"
                      }`}>
                        {shot.pass2_status}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleRenderSingleShot(shot.id, 1)}
                        disabled={isRenderingThis}
                        className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-mono border border-slate-700 transition-all disabled:opacity-50"
                      >
                        Re-render 360p
                      </button>
                      <button
                        onClick={() => handleRenderSingleShot(shot.id, 2)}
                        disabled={isRenderingThis}
                        className="px-2.5 py-1 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 text-[10px] font-mono border border-amber-500/30 transition-all disabled:opacity-50"
                      >
                        Render 720p
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Confirmation Modal: Pass 1 */}
      {showPass1Modal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0E111B] border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h3 className="font-bold text-white text-base flex items-center gap-2">
              <Zap className="w-5 h-5 text-amber-400" />
              <span>Confirm Pass 1 (360p Draft) Batch</span>
            </h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              This will render all 4 shots in 360p (9:16) for reviewing blocking, lip-sync, and prop placement.
            </p>
            <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 space-y-1 text-xs">
              <div className="flex justify-between text-slate-400 font-mono">
                <span>Cost:</span>
                <span className="text-amber-400 font-bold">$1.40 USD (140 Credits)</span>
              </div>
              <div className="flex justify-between text-slate-400 font-mono">
                <span>Shots:</span>
                <span className="text-white">4 clips x 15 seconds</span>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowPass1Modal(false)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-xs"
              >
                Cancel
              </button>
              <button
                onClick={handleBatchPass1}
                className="px-4 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs"
              >
                Confirm & Render Draft
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal: Pass 2 */}
      {showPass2Modal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0E111B] border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h3 className="font-bold text-white text-base flex items-center gap-2">
              <Video className="w-5 h-5 text-emerald-400" />
              <span>Confirm Pass 2 (720p Final) Batch</span>
            </h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              This will generate the high-resolution 720p (9:16) master passes for all approved shots.
            </p>
            <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 space-y-1 text-xs">
              <div className="flex justify-between text-slate-400 font-mono">
                <span>Cost:</span>
                <span className="text-emerald-400 font-bold">$4.16 USD (416 Credits)</span>
              </div>
              <div className="flex justify-between text-slate-400 font-mono">
                <span>Output:</span>
                <span className="text-white">720p Master Video Clips</span>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowPass2Modal(false)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-xs"
              >
                Cancel
              </button>
              <button
                onClick={handleBatchPass2}
                className="px-4 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs"
              >
                Confirm & Render Master
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
