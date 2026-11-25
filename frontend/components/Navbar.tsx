"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Clapperboard, Coins, Plus, History, X, CheckCircle2, RefreshCw } from "lucide-react";
import { API_BASE } from "@/lib/api";

interface LedgerEntry {
  id: number;
  amount: number;
  balance_after: number;
  reason: string;
  meta_info: string | null;
  created_at: string;
}

export default function Navbar() {
  const [balance, setBalance] = useState<number | null>(null);
  const [usdEquiv, setUsdEquiv] = useState<number | null>(null);
  const [apiMode, setApiMode] = useState<"live" | "mock" | "offline">("offline");
  const [showBilling, setShowBilling] = useState(false);
  const [ledger, setLedger] = useState<LedgerEntry[]>([]);
  const [loadingLedger, setLoadingLedger] = useState(false);
  const [toppingUp, setToppingUp] = useState(false);

  const fetchStatus = async () => {
    try {
      const [balRes, healthRes] = await Promise.all([
        fetch(`${API_BASE}/api/billing/balance`),
        fetch(`${API_BASE}/health`),
      ]);
      if (balRes.ok) {
        const data = await balRes.json();
        setBalance(data.credits_balance);
        setUsdEquiv(data.usd_equivalent);
      }
      if (healthRes.ok) {
        const h = await healthRes.json();
        setApiMode(h.api_mode === "live" ? "live" : "mock");
      }
    } catch {
      setApiMode("offline");
    }
  };

  const fetchLedger = async () => {
    try {
      setLoadingLedger(true);
      const res = await fetch(`${API_BASE}/api/billing/ledger?limit=25`);
      if (res.ok) {
        setLedger(await res.json());
      }
    } finally {
      setLoadingLedger(false);
    }
  };

  const handleTopUp = async (amount: number) => {
    try {
      setToppingUp(true);
      const res = await fetch(`${API_BASE}/api/billing/topup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount }),
      });
      if (res.ok) {
        const data = await res.json();
        setBalance(data.credits_balance);
        setUsdEquiv(data.usd_equivalent);
        await fetchLedger();
      }
    } finally {
      setToppingUp(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const handleUpdate = () => fetchStatus();
    window.addEventListener("creditBalanceUpdated", handleUpdate);
    return () => window.removeEventListener("creditBalanceUpdated", handleUpdate);
  }, []);

  const openBilling = () => {
    setShowBilling(true);
    fetchLedger();
  };

  return (
    <>
      <header className="sticky top-0 z-50 backdrop-blur-md bg-[#0B0D14]/90 border-b border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2.5 group">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-600 via-amber-500 to-yellow-400 p-[2px] shadow-lg shadow-amber-500/20 group-hover:shadow-amber-500/40 transition-all">
                <div className="w-full h-full bg-[#0B0D14] rounded-[10px] flex items-center justify-center">
                  <Clapperboard className="w-5 h-5 text-amber-400" />
                </div>
              </div>
              <div>
                <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-amber-200 bg-clip-text text-transparent">
                  MicroDrama{" "}
                  <span className="text-amber-400 text-xs font-semibold px-1.5 py-0.5 rounded bg-amber-400/10 border border-amber-400/20 ml-1">
                    STUDIO
                  </span>
                </span>
                <p className="text-[10px] text-slate-400 font-mono tracking-wider uppercase">
                  60s Vertical Pipeline v2.0
                </p>
              </div>
            </Link>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-xs font-medium text-slate-300">
              <span
                className={`w-2 h-2 rounded-full ${
                  apiMode === "live"
                    ? "bg-emerald-500 animate-pulse"
                    : apiMode === "mock"
                    ? "bg-amber-400"
                    : "bg-rose-500"
                }`}
              />
              <span>
                {apiMode === "live"
                  ? "Gemini Omni 1.2 Flash LIVE"
                  : apiMode === "mock"
                  ? "Studio Mock Mode"
                  : "Backend Offline"}
              </span>
            </div>

            <button
              onClick={openBilling}
              title="Click to manage credits & view ledger"
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-300 font-mono text-sm shadow-sm shadow-amber-500/10 transition-all cursor-pointer"
            >
              <Coins className="w-4 h-4 text-amber-400" />
              <span>{balance !== null ? balance.toLocaleString() : "..."} Credits</span>
              <span className="text-xs text-amber-400/60 font-sans hidden xs:inline">
                (${usdEquiv !== null ? usdEquiv.toFixed(2) : "0.00"})
              </span>
            </button>
          </div>
        </div>
      </header>

      {/* Billing & Credit Ledger Modal */}
      {showBilling && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0E111B] border border-slate-800 rounded-2xl max-w-xl w-full p-6 space-y-5 shadow-2xl max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Coins className="w-5 h-5 text-amber-400" />
                  <span>Studio Credits & Billing Ledger</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Pass 1 (360p): 35 credits ($0.35/15s) &bull; Pass 2 (720p): 104 credits ($1.04/15s)
                </p>
              </div>
              <button
                onClick={() => setShowBilling(false)}
                className="text-slate-400 hover:text-white p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Balance & Top-up */}
            <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <span className="text-[11px] font-mono text-slate-400 uppercase">Current Balance</span>
                <p className="text-2xl font-extrabold text-amber-400 font-mono">
                  {balance?.toLocaleString() ?? 0}{" "}
                  <span className="text-sm text-slate-400 font-sans">
                    credits (${usdEquiv?.toFixed(2) ?? "0.00"})
                  </span>
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {[500, 1000, 5000].map((amt) => (
                  <button
                    key={amt}
                    onClick={() => handleTopUp(amt)}
                    disabled={toppingUp}
                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-300 text-xs font-bold transition-all cursor-pointer disabled:opacity-50"
                  >
                    <Plus className="w-3 h-3" />
                    <span>{amt.toLocaleString()}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Transaction Ledger */}
            <div className="flex-1 overflow-y-auto space-y-2 pr-1">
              <div className="flex items-center justify-between text-xs font-mono text-slate-400 uppercase">
                <span className="flex items-center gap-1.5">
                  <History className="w-3.5 h-3.5 text-amber-400" />
                  <span>Recent Transactions</span>
                </span>
                <button
                  onClick={fetchLedger}
                  className="text-amber-400 hover:text-amber-300 flex items-center gap-1"
                >
                  <RefreshCw className={`w-3 h-3 ${loadingLedger ? "animate-spin" : ""}`} />
                  <span>Refresh</span>
                </button>
              </div>

              {loadingLedger ? (
                <div className="py-8 text-center text-xs text-slate-500">Loading ledger...</div>
              ) : ledger.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-500">No transactions yet.</div>
              ) : (
                <div className="divide-y divide-slate-800/70 rounded-xl border border-slate-800 bg-slate-950/50">
                  {ledger.map((item) => (
                    <div key={item.id} className="p-3 flex items-center justify-between gap-3 text-xs">
                      <div className="min-w-0">
                        <p className="text-slate-200 font-medium truncate">{item.reason}</p>
                        <p className="text-[10px] text-slate-500 font-mono">
                          {new Date(item.created_at).toLocaleString()}
                          {item.meta_info ? ` • ${item.meta_info}` : ""}
                        </p>
                      </div>
                      <div className="text-right shrink-0 font-mono">
                        <span
                          className={`font-bold ${
                            item.amount >= 0 ? "text-emerald-400" : "text-amber-400"
                          }`}
                        >
                          {item.amount >= 0 ? `+${item.amount}` : item.amount}
                        </span>
                        <p className="text-[10px] text-slate-500">Bal: {item.balance_after}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
