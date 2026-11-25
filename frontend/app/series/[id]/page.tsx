"use client";

import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Sparkles,
  Upload,
  RefreshCw,
  Film,
  User,
  MapPin,
  CheckCircle,
  Plus,
  ArrowRight,
  ShieldAlert,
  Sliders
} from "lucide-react";
import { API_BASE } from "@/lib/api";

interface Character {
  id: number;
  name: string;
  role_description: string;
  visual_tags: string;
  portrait_image_url: string | null;
  body_image_url: string | null;
  default_screen_position: string;
}

interface LocationItem {
  id: number;
  name: string;
  visual_tags: string;
  angle_a_image_url: string | null;
  angle_b_image_url: string | null;
}

interface SeriesData {
  id: number;
  title: string;
  premise: string;
  genre: string;
  locked_lighting: string;
  characters: Character[];
  locations: LocationItem[];
}

interface EpisodeItem {
  id: number;
  episode_number: number;
  title: string;
  premise: string;
  status: string;
}

export default function SeriesVisualBiblePage() {
  const params = useParams();
  const router = useRouter();
  const seriesId = params.id as string;

  const [series, setSeries] = useState<SeriesData | null>(null);
  const [episodes, setEpisodes] = useState<EpisodeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [generatingAll, setGeneratingAll] = useState(false);
  const [regeneratingAsset, setRegeneratingAsset] = useState<string | null>(null);
  const [uploadingAsset, setUploadingAsset] = useState<string | null>(null);

  // New episode modal
  const [showEpModal, setShowEpModal] = useState(false);
  const [epTitle, setEpTitle] = useState("Episode 1: The Revelation");
  const [epPremise, setEpPremise] = useState("The undercover heir is confronted with a document proving his rival's company bought his family debt.");

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [uploadTarget, setUploadTarget] = useState<{ assetType: string; targetId: number } | null>(null);

  const fetchSeriesData = async () => {
    try {
      setLoading(true);
      const [resSeries, resEpisodes] = await Promise.all([
        fetch(`${API_BASE}/api/series/${seriesId}`),
        fetch(`${API_BASE}/api/episodes/series/${seriesId}`)
      ]);

      if (resSeries.ok) {
        const sData = await resSeries.json();
        setSeries(sData);
      }
      if (resEpisodes.ok) {
        const epData = await resEpisodes.json();
        setEpisodes(epData);
      }
    } catch (err) {
      console.error("Error loading series:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (seriesId) {
      fetchSeriesData();
    }
  }, [seriesId]);

  const handleGenerateAll = async () => {
    try {
      setGeneratingAll(true);
      const res = await fetch(`${API_BASE}/api/series/${seriesId}/visual-bible/generate-all`, {
        method: "POST"
      });
      if (res.ok) {
        await fetchSeriesData();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setGeneratingAll(false);
    }
  };

  const handleRegenerateSingle = async (assetType: string, targetId: number) => {
    const key = `${assetType}_${targetId}`;
    try {
      setRegeneratingAsset(key);
      const res = await fetch(`${API_BASE}/api/series/${seriesId}/visual-bible/regenerate-asset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ asset_type: assetType, target_id: targetId })
      });
      if (res.ok) {
        await fetchSeriesData();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setRegeneratingAsset(null);
    }
  };

  const triggerUpload = (assetType: string, targetId: number) => {
    setUploadTarget({ assetType, targetId });
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
      fileInputRef.current.click();
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !uploadTarget) return;

    const key = `${uploadTarget.assetType}_${uploadTarget.targetId}`;
    try {
      setUploadingAsset(key);
      const formData = new FormData();
      formData.append("asset_type", uploadTarget.assetType);
      formData.append("target_id", uploadTarget.targetId.toString());
      formData.append("file", file);

      const res = await fetch(`${API_BASE}/api/series/${seriesId}/visual-bible/upload-asset`, {
        method: "POST",
        body: formData
      });
      if (res.ok) {
        await fetchSeriesData();
      }
    } catch (err) {
      console.error("Upload failed:", err);
    } finally {
      setUploadingAsset(null);
      setUploadTarget(null);
    }
  };

  const handleCreateEpisode = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const nextNum = episodes.length + 1;
      const res = await fetch(`${API_BASE}/api/episodes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          series_id: Number(seriesId),
          title: epTitle,
          premise: epPremise,
          episode_number: nextNum
        })
      });
      if (res.ok) {
        const newEp = await res.json();
        setShowEpModal(false);
        router.push(`/episode/${newEp.id}`);
      }
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center text-slate-400 space-y-3">
        <RefreshCw className="w-8 h-8 animate-spin mx-auto text-amber-400" />
        <p className="font-mono text-sm">Loading Visual Bible...</p>
      </div>
    );
  }

  if (!series) {
    return (
      <div className="py-12 text-center text-slate-400">
        <p>Series not found.</p>
        <Link href="/" className="text-amber-400 text-xs underline mt-2 inline-block">
          Return to Dashboard
        </Link>
      </div>
    );
  }

  const charA = series.characters?.[0];
  const charB = series.characters?.[1];
  const primaryLoc = series.locations?.[0];

  const assetCards = [
    {
      title: charA ? `${charA.name} - Portrait` : "Char A: Portrait",
      subtitle: `Screen-Position: ${charA?.default_screen_position || "RIGHT"}`,
      url: charA?.portrait_image_url,
      assetType: "char_portrait",
      targetId: charA?.id,
      icon: User,
      badge: "Anchor 1/6"
    },
    {
      title: charA ? `${charA.name} - Full Body` : "Char A: Full Body",
      subtitle: "Identity-locked 9:16 posture",
      url: charA?.body_image_url,
      assetType: "char_body",
      targetId: charA?.id,
      icon: User,
      badge: "Anchor 2/6"
    },
    {
      title: charB ? `${charB.name} - Portrait` : "Char B: Portrait",
      subtitle: `Screen-Position: ${charB?.default_screen_position || "LEFT"}`,
      url: charB?.portrait_image_url,
      assetType: "char_portrait",
      targetId: charB?.id,
      icon: User,
      badge: "Anchor 3/6"
    },
    {
      title: charB ? `${charB.name} - Full Body` : "Char B: Full Body",
      subtitle: "Identity-locked 9:16 posture",
      url: charB?.body_image_url,
      assetType: "char_body",
      targetId: charB?.id,
      icon: User,
      badge: "Anchor 4/6"
    },
    {
      title: primaryLoc ? `${primaryLoc.name} (Angle A)` : "Location: Angle A",
      subtitle: "Front View Master Set",
      url: primaryLoc?.angle_a_image_url,
      assetType: "loc_angle_a",
      targetId: primaryLoc?.id,
      icon: MapPin,
      badge: "Anchor 5/6"
    },
    {
      title: primaryLoc ? `${primaryLoc.name} (Angle B)` : "Location: Angle B",
      subtitle: "180° Reverse Opposite View",
      url: primaryLoc?.angle_b_image_url,
      assetType: "loc_angle_b",
      targetId: primaryLoc?.id,
      icon: MapPin,
      badge: "Anchor 6/6"
    }
  ];

  const lockedCount = assetCards.filter((a) => a.url).length;

  return (
    <div className="space-y-8">
      {/* Hidden file input for manual upload */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        accept="image/*"
        className="hidden"
      />

      {/* Top Navigation & Info */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Dashboard</span>
        </Link>
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-slate-400">
            Locked Bible: <span className="text-amber-400 font-bold">{lockedCount}/6</span> Assets
          </span>
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
            180° Spatial Rule Active
          </span>
        </div>
      </div>

      {/* Series Hero Card */}
      <div className="rounded-2xl bg-slate-900/90 border border-slate-800 p-6 space-y-4">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div className="space-y-2 max-w-3xl">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs font-semibold">
                {series.genre}
              </span>
              <span className="text-xs text-slate-500 font-mono">Series #{series.id}</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              {series.title}
            </h1>
            <p className="text-sm text-slate-300 leading-relaxed">{series.premise}</p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={handleGenerateAll}
              disabled={generatingAll}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold text-xs shadow-lg shadow-amber-500/20 disabled:opacity-50 transition-all cursor-pointer"
            >
              {generatingAll ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Locking All 6 Assets...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Generate All 6 Bible Anchors</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Locked Lighting String Rule Banner */}
        <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800/80 flex items-start gap-3">
          <Sliders className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
          <div className="text-xs space-y-1">
            <span className="font-semibold text-amber-300 uppercase tracking-wider font-mono text-[11px]">
              Locked Lighting Spec (Auto-Appended to Omni Prompts):
            </span>
            <p className="text-slate-400 font-mono text-[11px]">{series.locked_lighting}</p>
          </div>
        </div>
      </div>

      {/* 6-Asset Visual Bible Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Film className="w-5 h-5 text-amber-400" />
            <span>Strict 6-Asset Visual Bible (Nano Banana Reference Anchors)</span>
          </h2>
          <span className="text-xs text-slate-500 font-mono">
            Passed to Gemini Omni (max 6 images/shot)
          </span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {assetCards.map((asset, idx) => {
            const isRegen = regeneratingAsset === `${asset.assetType}_${asset.targetId}`;
            const isUpload = uploadingAsset === `${asset.assetType}_${asset.targetId}`;
            const Icon = asset.icon;

            return (
              <div
                key={idx}
                className="group relative rounded-xl bg-slate-900 border border-slate-800 overflow-hidden flex flex-col justify-between hover:border-amber-500/40 transition-all shadow-md"
              >
                {/* Badge */}
                <div className="absolute top-2 left-2 z-10 px-2 py-0.5 rounded-full bg-black/70 backdrop-blur-md border border-slate-700/80 text-[10px] font-mono text-amber-300">
                  {asset.badge}
                </div>

                {/* Image Container 9:16 */}
                <div className="relative aspect-[9/16] w-full bg-slate-950 flex items-center justify-center overflow-hidden">
                  {asset.url ? (
                    <img
                      src={`${API_BASE}${asset.url}`}
                      alt={asset.title}
                      className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                    />
                  ) : (
                    <div className="p-4 text-center space-y-2 text-slate-500">
                      <Icon className="w-8 h-8 mx-auto opacity-40" />
                      <span className="block text-[10px] font-mono">Unrendered</span>
                    </div>
                  )}

                  {/* Loading overlay */}
                  {(isRegen || isUpload) && (
                    <div className="absolute inset-0 bg-black/80 backdrop-blur-sm flex flex-col items-center justify-center p-3 text-center space-y-2 z-20">
                      <RefreshCw className="w-6 h-6 animate-spin text-amber-400" />
                      <span className="text-[10px] font-mono text-amber-300">
                        {isUpload ? "Uploading..." : "Synthesizing..."}
                      </span>
                    </div>
                  )}
                </div>

                {/* Card Meta & Actions */}
                <div className="p-3 bg-slate-900 border-t border-slate-800 space-y-2">
                  <div>
                    <h3 className="text-xs font-bold text-white truncate">{asset.title}</h3>
                    <p className="text-[10px] text-slate-400 truncate">{asset.subtitle}</p>
                  </div>

                  <div className="flex items-center gap-1.5 pt-1">
                    <button
                      onClick={() => asset.targetId && handleRegenerateSingle(asset.assetType, asset.targetId)}
                      disabled={isRegen || isUpload || !asset.targetId}
                      title="Regenerate with Nano Banana"
                      className="flex-1 py-1.5 px-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-[10px] font-semibold text-slate-300 flex items-center justify-center gap-1 transition-all disabled:opacity-50"
                    >
                      <RefreshCw className="w-3 h-3 text-amber-400" />
                      <span>Regen</span>
                    </button>
                    <button
                      onClick={() => asset.targetId && triggerUpload(asset.assetType, asset.targetId)}
                      disabled={isRegen || isUpload || !asset.targetId}
                      title="Upload custom image"
                      className="py-1.5 px-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-[10px] text-slate-300 flex items-center justify-center transition-all disabled:opacity-50"
                    >
                      <Upload className="w-3 h-3 text-slate-400 hover:text-white" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Episodes Production Table */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Film className="w-5 h-5 text-amber-400" />
              <span>Episodes Production (60s Vertical Pipeline)</span>
            </h2>
            <p className="text-xs text-slate-400">
              Each episode contains 4 x 15s shots rendered across 2 passes (360p &rarr; 720p).
            </p>
          </div>

          <button
            onClick={() => setShowEpModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs shadow-md shadow-amber-500/20"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Create Episode</span>
          </button>
        </div>

        {episodes.length === 0 ? (
          <div className="p-8 text-center border border-dashed border-slate-800 rounded-xl bg-slate-950/40">
            <p className="text-xs text-slate-400">No episodes created yet for this series.</p>
            <button
              onClick={() => setShowEpModal(true)}
              className="mt-3 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold text-slate-200"
            >
              Start Episode 1
            </button>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/80">
            {episodes.map((ep) => (
              <div
                key={ep.id}
                className="py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 group"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-amber-400">
                      EP #{ep.episode_number}
                    </span>
                    <h3 className="text-sm font-bold text-white group-hover:text-amber-300 transition-colors">
                      {ep.title}
                    </h3>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-300 border border-slate-700">
                      {ep.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-1">{ep.premise}</p>
                </div>

                <Link
                  href={`/episode/${ep.id}`}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 text-xs font-bold shadow-md shadow-amber-500/10 transition-all shrink-0"
                >
                  <span>Open Studio Desk</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Episode Creation Modal */}
      {showEpModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0E111B] border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-white text-base">New Episode Specification</h3>
              <button onClick={() => setShowEpModal(false)} className="text-slate-400 hover:text-white text-xs">
                ✕
              </button>
            </div>
            <form onSubmit={handleCreateEpisode} className="space-y-4">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-300">Episode Title</label>
                <input
                  type="text"
                  value={epTitle}
                  onChange={(e) => setEpTitle(e.target.value)}
                  required
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-amber-500"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-300">Episode Premise / Conflict</label>
                <textarea
                  rows={3}
                  value={epPremise}
                  onChange={(e) => setEpPremise(e.target.value)}
                  required
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-amber-500"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowEpModal(false)}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-xs font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold"
                >
                  Create & Direct Episode
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
