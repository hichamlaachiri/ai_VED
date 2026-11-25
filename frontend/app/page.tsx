"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus, Film, Sparkles, Tv, ArrowRight, Eye, RefreshCw, Trash2, Sliders } from "lucide-react";
import { API_BASE } from "@/lib/api";

interface Character {
  id: number;
  name: string;
  role_description: string;
  default_screen_position: string;
}

interface EpisodeBrief {
  id: number;
  episode_number: number;
  title: string;
  status: string;
}

interface SeriesItem {
  id: number;
  title: string;
  premise: string;
  genre: string;
  locked_lighting: string;
  created_at: string;
  characters: Character[];
  locations: any[];
  episodes: EpisodeBrief[];
}

export default function Dashboard() {
  const [seriesList, setSeriesList] = useState<SeriesItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // New series form
  const [title, setTitle] = useState("The CEO's Silent Heir");
  const [premise, setPremise] = useState(
    "A disguised billionaire works undercover as a junior valet at his family hotel, only to discover the rival heiress is uncovering his double life in the penthouse lounge."
  );
  const [genre, setGenre] = useState("Micro-Drama Thriller");
  const [lockedLighting, setLockedLighting] = useState(
    "High-contrast cinematic neo-noir lighting, soft warm fill with subtle teal rim lights, 8k shallow depth of field"
  );
  const [char1Name, setChar1Name] = useState("Julian Vance");
  const [char1Role, setChar1Role] = useState("Disguised billionaire heir, sharp jawline, intense gaze, charcoal valet jacket");
  const [char2Name, setChar2Name] = useState("Elena Rostova");
  const [char2Role, setChar2Role] = useState("Rival family heiress, platinum sleek bob, tailored emerald blazer, observant smile");
  const [locName, setLocName] = useState("Penthouse Lounge & Terrace");
  const [locTags, setLocTags] = useState("High-end skyscraper lounge at midnight, floor-to-ceiling glass windows overlooking neon city skyline");

  const fetchSeries = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/api/series`);
      if (res.ok) {
        const data = await res.json();
        setSeriesList(data);
      }
    } catch (e) {
      console.error("Failed to fetch series:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSeries();
  }, []);

  const handleCreateSeries = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        title,
        premise,
        genre,
        locked_lighting: lockedLighting,
        characters: [
          {
            name: char1Name,
            role_description: char1Role,
            visual_tags: char1Role,
            default_screen_position: "RIGHT",
          },
          {
            name: char2Name,
            role_description: char2Role,
            visual_tags: char2Role,
            default_screen_position: "LEFT",
          },
        ],
        location: {
          name: locName,
          visual_tags: locTags,
        },
      };

      const res = await fetch(`${API_BASE}/api/series`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        setShowCreateModal(false);
        fetchSeries();
      }
    } catch (err) {
      console.error("Failed to create series:", err);
    }
  };

  const handleDeleteSeries = async (seriesId: number, seriesTitle: string) => {
    if (!confirm(`Delete "${seriesTitle}" and all its episodes?`)) return;
    try {
      const res = await fetch(`${API_BASE}/api/series/${seriesId}`, { method: "DELETE" });
      if (res.ok) {
        fetchSeries();
      }
    } catch (err) {
      console.error("Failed to delete series:", err);
    }
  };

  return (
    <div className="space-y-8">
      {/* Hero Studio Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900/90 to-amber-950/40 border border-slate-800 p-8 shadow-2xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-amber-500/10 rounded-full blur-3xl -z-10"></div>
        <div className="max-w-3xl space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span>Google Gemini Omni 1.2 Flash Interactions Pipeline</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
            Produce 60-Second Vertical Micro-Dramas in Minutes
          </h1>
          <p className="text-slate-400 text-sm sm:text-base leading-relaxed">
            Locked Visual Bible consistency (max 3 characters + 2-angle location), 180° spatial blocking, 2-pass cost-optimized rendering (360p Draft &rarr; 720p Final), and FFmpeg auto-assembly.
          </p>
          <div className="pt-2 flex flex-wrap gap-3">
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-semibold text-sm shadow-lg shadow-amber-500/20 transition-all cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>Create New Series</span>
            </button>
            <button
              onClick={fetchSeries}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800/80 hover:bg-slate-700 border border-slate-700/60 text-slate-300 text-sm font-medium transition-all cursor-pointer"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Refresh Studio</span>
            </button>
          </div>
        </div>
      </div>

      {/* Series Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            <Film className="w-5 h-5 text-amber-400" />
            <span>Active Micro-Drama Series</span>
          </h2>
          <span className="text-xs text-slate-400 font-mono">
            {seriesList.length} Series Created
          </span>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-500 border border-slate-800/60 rounded-xl bg-slate-900/30">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-amber-400" />
            <p>Loading studio productions...</p>
          </div>
        ) : seriesList.length === 0 ? (
          <div className="p-12 text-center border border-dashed border-slate-800 rounded-2xl bg-slate-900/20 space-y-4">
            <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center mx-auto text-amber-400">
              <Tv className="w-6 h-6" />
            </div>
            <div>
              <h3 className="font-semibold text-slate-200">No Micro-Drama Series Yet</h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1">
                Start by setting up your Visual Bible with locked character anchors and 2-angle sets.
              </p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-500 text-slate-950 font-semibold text-xs"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Create Series</span>
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {seriesList.map((item) => {
              const latestEp = item.episodes && item.episodes.length > 0 ? item.episodes[item.episodes.length - 1] : null;
              return (
                <div
                  key={item.id}
                  className="group relative rounded-2xl bg-slate-900/80 border border-slate-800/80 hover:border-amber-500/40 p-6 flex flex-col justify-between transition-all duration-300 hover:shadow-xl hover:shadow-amber-500/5"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-xs">
                      <span className="px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-300 font-medium">
                        {item.genre}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-slate-500 font-mono text-[11px]">
                          {item.episodes?.length || 0} ep
                        </span>
                        <button
                          onClick={() => handleDeleteSeries(item.id, item.title)}
                          title="Delete Series"
                          className="text-slate-600 hover:text-rose-400 transition-colors cursor-pointer"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    <h3 className="text-lg font-bold text-white group-hover:text-amber-300 transition-colors">
                      {item.title}
                    </h3>

                    <p className="text-xs text-slate-400 line-clamp-3 leading-relaxed">
                      {item.premise}
                    </p>

                    <div className="pt-2 border-t border-slate-800/60 space-y-1.5">
                      <div className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">
                        Locked Visual Assets:
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {item.characters?.map((c) => (
                          <span
                            key={c.id}
                            className="text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700/60 flex items-center gap-1"
                          >
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                            {c.name} ({c.default_screen_position})
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="pt-6 flex items-center justify-between gap-3">
                    <Link
                      href={`/series/${item.id}`}
                      className="flex-1 inline-flex items-center justify-center gap-2 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700/80 text-xs font-semibold text-slate-200 transition-all"
                    >
                      <Eye className="w-3.5 h-3.5 text-amber-400" />
                      <span>Visual Bible</span>
                    </Link>
                    {latestEp ? (
                      <Link
                        href={`/episode/${latestEp.id}`}
                        className="flex-1 inline-flex items-center justify-center gap-2 px-3 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-xs font-bold text-slate-950 transition-all shadow-md shadow-amber-500/10"
                      >
                        <span>EP #{latestEp.episode_number} Desk</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    ) : (
                      <Link
                        href={`/series/${item.id}`}
                        className="flex-1 inline-flex items-center justify-center gap-2 px-3 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-xs font-bold text-slate-950 transition-all shadow-md shadow-amber-500/10"
                      >
                        <span>Start Ep 1</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Create Series Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-[#0E111B] border border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-5 shadow-2xl my-8">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Film className="w-5 h-5 text-amber-400" />
                  <span>Create Micro-Drama Series</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Establishes the Visual Bible, locked lighting string, and strict 180° spatial constraints.
                </p>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateSeries} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300">Series Title</label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    required
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-sm text-slate-200 focus:outline-none focus:border-amber-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300">Genre</label>
                  <input
                    type="text"
                    value={genre}
                    onChange={(e) => setGenre(e.target.value)}
                    required
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-sm text-slate-200 focus:outline-none focus:border-amber-500"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-300">Logline / Premise</label>
                <textarea
                  rows={2}
                  value={premise}
                  onChange={(e) => setPremise(e.target.value)}
                  required
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-sm text-slate-200 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-amber-300 flex items-center gap-1.5">
                  <Sliders className="w-3.5 h-3.5" />
                  <span>Locked Lighting String (Appended to Every Prompt)</span>
                </label>
                <input
                  type="text"
                  value={lockedLighting}
                  onChange={(e) => setLockedLighting(e.target.value)}
                  required
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-slate-200 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
                <div className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center justify-between">
                  <span>Character Anchors (180° Rule)</span>
                  <span className="text-[10px] text-slate-400 lowercase font-normal">max 3 characters</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-[11px] text-slate-400 font-mono">Char A (Locked RIGHT)</label>
                    <input
                      type="text"
                      placeholder="Character Name"
                      value={char1Name}
                      onChange={(e) => setChar1Name(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-200"
                    />
                    <input
                      type="text"
                      placeholder="Role & Key visual markers"
                      value={char1Role}
                      onChange={(e) => setChar1Role(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-200"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[11px] text-slate-400 font-mono">Char B (Locked LEFT)</label>
                    <input
                      type="text"
                      placeholder="Character Name"
                      value={char2Name}
                      onChange={(e) => setChar2Name(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-200"
                    />
                    <input
                      type="text"
                      placeholder="Role & Key visual markers"
                      value={char2Role}
                      onChange={(e) => setChar2Role(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-200"
                    />
                  </div>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                <div className="text-xs font-bold text-amber-400 uppercase tracking-wider">
                  Primary Location (Angle A + Angle B)
                </div>
                <input
                  type="text"
                  placeholder="Location Name"
                  value={locName}
                  onChange={(e) => setLocName(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-200"
                />
                <input
                  type="text"
                  placeholder="Architectural & Lighting Details"
                  value={locTags}
                  onChange={(e) => setLocTags(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-200"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold shadow-lg shadow-amber-500/20"
                >
                  Initialize Visual Bible
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
